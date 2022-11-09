# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import sys
sys.path.insert(0, "../")
from datetime import datetime
from sqlite3 import Date
from datatypes_date_time.timex import Timex
from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
    DialogManager,
    DialogManagerResult,
    Dialog

)
from botbuilder.core import (
    AutoSaveStateMiddleware,
    BotAdapter,
    ConversationState,
    MemoryStorage,
    MessageFactory,
    UserState,
    TurnContext,
)
from botbuilder.dialogs.prompts import (
    TextPrompt,
    NumberPrompt,
    ChoicePrompt,
    ConfirmPrompt,
    AttachmentPrompt,
    PromptOptions,
    PromptValidatorContext,
)
from .cancel_and_help_dialog import CancelAndHelpDialog
from enum import Enum
from typing import Callable, List, Tuple
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from botbuilder.core import MessageFactory, UserState
from botbuilder.core.adapters import TestAdapter
from botbuilder.core.skills import SkillHandler, SkillConversationReference


from botbuilder.core.adapters import TestAdapter
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    ChannelAccount,
    ConversationAccount,
    EndOfConversationCodes,
    InputHints,
)
import sys
from botframework.connector.auth import AuthenticationConstants, ClaimsIdentity
from helpers.date_resolver_dialog import DateResolverDialog
from user_profile import UserProfile

class Questions(str, Enum):
    destination = "To what city would you like to travel?"
    origin = "From what city will you be travelling?"
    budget = "Please enter your budget."


class SkillFlowTestCase(str, Enum):
    # DialogManager is executing on a root bot with no skills (typical standalone bot).
    root_bot_only = "RootBotOnly"

    # DialogManager is executing on a root bot handling replies from a skill.
    root_bot_consuming_skill = "RootBotConsumingSkill"

    # DialogManager is executing in a skill that is called from a root and calling another skill.
    middle_skill = "MiddleSkill"

    # DialogManager is executing in a skill that is called from a parent (a root or another skill) but doesn"t call
    # another skill.
    leaf_skill = "LeafSkill"



class UserProfileDialog(CancelAndHelpDialog):
    # An App ID for a parent bot.
    parent_bot_id = "00000000-0000-0000-0000-0000000000PARENT"

    # An App ID for a skill bot.
    skill_bot_id = "00000000-0000-0000-0000-00000000000SKILL"

    # Captures an EndOfConversation if it was sent to help with assertions.
    eoc_sent: Activity = None

    # Property to capture the DialogManager turn results and do assertions.
    dm_turn_result: DialogManagerResult = UserProfile()

    def __init__(
        self,
        dialog_id: str = None,
        telemetry_client: BotTelemetryClient = NullTelemetryClient(),
        ):
        super(UserProfileDialog, self).__init__(
            dialog_id or UserProfileDialog.__name__,
            telemetry_client)

        #self.user_profile_accessor = user_state.create_property("UserProfile")
        # information in appinsight
        self.telemetry_client = telemetry_client
        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = telemetry_client
        waterfall_dialog = WaterfallDialog(
                WaterfallDialog.__name__,
                [
                    self.destination_step,
                    self.origin_step,
                    self.travel_date_str_step,
                    self.travel_date_end_step,
                    self.budget_step,
                    self.final_step,
                ],
            )
        
        #for app insight
        waterfall_dialog.telemetry_client = telemetry_client
        self.add_dialog(text_prompt)
        self.add_dialog(
            DateResolverDialog(DateResolverDialog.__name__, self.telemetry_client)
        )
        self.add_dialog(waterfall_dialog)
        self.initial_dialog_id = WaterfallDialog.__name__

        #dialog
        self.add_dialog(
             NumberPrompt(NumberPrompt.__name__, UserProfileDialog.budget_prompt_validator)
        )
        #self.add_dialog(ChoicePrompt(ChoicePrompt.__name__))
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        # self.add_dialog(
        #     AttachmentPrompt(
        #         AttachmentPrompt.__name__, UserProfileDialog.picture_prompt_validator
        #     )
        # )

        self.initial_dialog_id = WaterfallDialog.__name__
        self.end_reason = None
    
    @staticmethod
    async def create_test_flow(
        dialog: Dialog,
        test_case: SkillFlowTestCase = SkillFlowTestCase.root_bot_only,
        enabled_trace=False
    ) -> TestAdapter:
        conversation_id = "testFlowConversationId"
        storage = MemoryStorage()
        conversation_state = ConversationState(storage)
        user_state = UserState(storage)
        
        activity = Activity(
            channel_id="test",
            service_url="https://test.com",
            from_property=ChannelAccount(id="user1", name="User1"),
            recipient=ChannelAccount(id="bot", name="Bot"),
            conversation=ConversationAccount(
                is_group=False, conversation_type=conversation_id, id=conversation_id
            )
        )

        dialog_manager = DialogManager(dialog)
        dialog_manager.user_state = user_state
        dialog_manager.conversation_state = conversation_state

        async def logic(context: TurnContext):
            if test_case != SkillFlowTestCase.root_bot_only:
                # Create a skill ClaimsIdentity and put it in turn_state so isSkillClaim() returns True.
                claims_identity = ClaimsIdentity({}, False)
                claims_identity.claims[
                    "ver"
                ] = "2.0"  # AuthenticationConstants.VersionClaim
                claims_identity.claims[
                    "aud"
                ] = (
                    UserProfileDialog.skill_bot_id
                )  # AuthenticationConstants.AudienceClaim
                claims_identity.claims[
                    "azp"
                ] = (
                    UserProfileDialog.parent_bot_id
                )  # AuthenticationConstants.AuthorizedParty
                context.turn_state[BotAdapter.BOT_IDENTITY_KEY] = claims_identity
                if test_case == SkillFlowTestCase.root_bot_consuming_skill:
                    # Simulate the SkillConversationReference with a channel OAuthScope stored in turn_state.
                    # This emulates a response coming to a root bot through SkillHandler.
                    context.turn_state[
                        SkillHandler.SKILL_CONVERSATION_REFERENCE_KEY
                    ] = SkillConversationReference(
                        None, AuthenticationConstants.TO_CHANNEL_FROM_BOT_OAUTH_SCOPE
                    )

                if test_case == SkillFlowTestCase.middle_skill:
                    # Simulate the SkillConversationReference with a parent Bot ID stored in turn_state.
                    # This emulates a response coming to a skill from another skill through SkillHandler.
                    context.turn_state[
                        SkillHandler.SKILL_CONVERSATION_REFERENCE_KEY
                    ] = SkillConversationReference(
                        None, UserProfileDialog.parent_bot_id
                    )

            async def aux(
                turn_context: TurnContext,  # pylint: disable=unused-argument
                activities: List[Activity],
                next: Callable,
            ):
                for activity in activities:
                    if activity.type == ActivityTypes.end_of_conversation:
                        UserProfileDialog.eoc_sent = activity
                        break

                return await next()

            # Interceptor to capture the EoC activity if it was sent so we can assert it in the tests.
            context.on_send_activities(aux)
            UserProfileDialog.dm_turn_result = await dialog_manager.on_turn(context)
        adapter = TestAdapter(logic, activity, enabled_trace)
        adapter.use(AutoSaveStateMiddleware([user_state, conversation_state]))

        return adapter

    async def destination_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        # WaterfallStep always finishes with the end of the Waterfall or with another dialog;
        # here it is a Prompt Dialog. Running a prompt here means the next WaterfallStep will
        # be run when the users response is received.
        booking_details = step_context.options

        if booking_details is not None:
            if booking_details.destination is None:
                return await step_context.prompt(
                    TextPrompt.__name__,
                    PromptOptions(
                        prompt=MessageFactory.text(Questions.destination)
                    ),
                )
            else:
                return await step_context.next(booking_details.destination)
        else:            
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text(Questions.destination)
                ),
            )
        return await step_context.next(booking_details.destination)


    async def origin_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for origin city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        if booking_details is not None:
            booking_details.destination = step_context.result
        else:
            booking_details = UserProfile()
            booking_details.destination = step_context.result
        if booking_details.origin is None:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text(Questions.origin)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.origin)

    async def travel_date_str_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options
        if booking_details is not None:
            # Capture the results of the previous step
            booking_details.origin = step_context.result
        else:
            booking_details = UserProfile()
            booking_details.origin = step_context.result
        if not booking_details.travel_date_str or self.is_ambiguous(
            booking_details.travel_date_str
        ):
            return await step_context.begin_dialog(
                DateResolverDialog.__name__, booking_details.travel_date_str
            )  # pylint: disable=line-too-long
        return await step_context.next(booking_details.travel_date_str)

    async def travel_date_end_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""
        booking_details = step_context.options

        if booking_details is not None:
            booking_details.travel_date_str = step_context.result
        else:
            booking_details = UserProfile()
            booking_details.travel_date_str = step_context.result

        if not booking_details.travel_date_end or self.is_ambiguous(
            booking_details.travel_date_end
        ):
            return await step_context.begin_dialog(
                DateResolverDialog.__name__, booking_details.travel_date_end
            )  # pylint: disable=line-too-long

        return await step_context.next(booking_details.travel_date_end)


    async def budget_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # User said "yes" so we will be prompting for the age.
        # WaterfallStep always finishes with the end of the Waterfall or with another dialog,
        # here it is a Prompt Dialog.
        booking_details = step_context.options
        if booking_details is not None:
            booking_details.travel_date_end = step_context.result
        else:
            booking_details=UserProfile()
            booking_details.travel_date_end = step_context.result
        if booking_details.budget is None:
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("Please enter your budget."),
                    retry_prompt=MessageFactory.text(
                        "The value entered must be greater than 0 and must be a number."
                    ),
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.budget)


    async def confirm_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        step_context.values["picture"] = (
            None if not step_context.result else step_context.result[0]
        )

        # WaterfallStep always finishes with the end of the Waterfall or
        # with another dialog; here it is a Prompt Dialog.
        return await step_context.prompt(
            ConfirmPrompt.__name__,
            PromptOptions(prompt=MessageFactory.text("Is this ok?")),
        )


    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        if step_context.result:
            booking_details = step_context.options
            if booking_details is not None:
                booking_details.budget = step_context.result
            else:
                booking_details=UserProfile()
                booking_details.budget = step_context.result

            return await step_context.end_dialog(booking_details)

        return await step_context.end_dialog()

    def is_ambiguous(self, timex: str) -> bool:
        """Ensure time is correct."""
        timex_property = Timex(timex)
        return "definite" not in timex_property.types

    @staticmethod
    async def budget_prompt_validator(prompt_context: PromptValidatorContext) -> bool:
        # This condition is our validation rule. You can also change the value at this point.
        return (
            prompt_context.recognized.succeeded
            and 0 < prompt_context.recognized.value
        )

    @staticmethod
    async def end_date_prompt_validator(prompt_context: PromptValidatorContext) -> bool:
        # This condition is our validation rule. You can also change the value at this point.
        
        return (
            prompt_context.recognized.succeeded
            and 0 < prompt_context.recognized.value
        )
