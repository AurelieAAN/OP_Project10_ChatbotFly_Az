# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import warnings
from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    DialogManagerResult,
    WaterfallStepContext,
    DialogManager,
    Dialog,
    DialogTurnResult,
)
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    ChannelAccount,
    ConversationAccount,
    EndOfConversationCodes,
    InputHints,
)
from botframework.connector.auth import AuthenticationConstants, ClaimsIdentity
from botbuilder.dialogs.prompts import TextPrompt, PromptOptions
from botbuilder.core import (
    MessageFactory,
    TurnContext,
    BotTelemetryClient,
    NullTelemetryClient,
)
from botbuilder.dialogs.prompts import (
    TextPrompt,
    ConfirmPrompt,
    PromptOptions
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
from botbuilder.core.adapters import TestAdapter
from botbuilder.core.skills import SkillHandler, SkillConversationReference
from botbuilder.schema import InputHints
from typing import Callable, List, Tuple
from OP_Project10_ChatbotFly_Az.flight_booking_recognizer import FlightBookingRecognizer
from OP_Project10_ChatbotFly_Az.helpers.luis_helper import LuisHelper, Intent
from .user_profile_dialog import UserProfileDialog
import logging
from OP_Project10_ChatbotFly_Az.config import DefaultConfig
from opencensus.ext.azure.log_exporter import AzureEventHandler
from enum import Enum
CONFIG = DefaultConfig()

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

class MainDialog(ComponentDialog):
    # An App ID for a parent bot.
    parent_bot_id = "00000000-0000-0000-0000-0000000000PARENT"

    # An App ID for a skill bot.
    skill_bot_id = "00000000-0000-0000-0000-00000000000SKILL"

    # Captures an EndOfConversation if it was sent to help with assertions.
    eoc_sent: Activity = None

    # Property to capture the DialogManager turn results and do assertions.
    dm_turn_result: DialogManagerResult = None
    def __init__(
        self,
        luis_recognizer: FlightBookingRecognizer, # à vérifier
        booking_dialog: UserProfileDialog,
        telemetry_client: BotTelemetryClient = None,
    ):
        super(MainDialog, self).__init__(MainDialog.__name__)
        self.telemetry_client = telemetry_client or NullTelemetryClient()

        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = self.telemetry_client

        confirm_prompt = ConfirmPrompt(ConfirmPrompt.__name__)
        confirm_prompt.telemetry_client = self.telemetry_client

        booking_dialog.telemetry_client = self.telemetry_client

        wf_dialog = WaterfallDialog(
            "WFDialog", [self.intro_step, self.act_step, self.recap_step, self.final_step]
        )
        wf_dialog.telemetry_client = self.telemetry_client

        self._luis_recognizer = luis_recognizer
        self._booking_dialog_id = booking_dialog.id

        self.add_dialog(text_prompt)
        self.add_dialog(confirm_prompt)
        self.add_dialog(booking_dialog)
        self.add_dialog(wf_dialog)

        self.initial_dialog_id = "WFDialog"
        self.end_reason = None
    
    @staticmethod
    async def create_test_flow(
        dialog: Dialog,
        test_case: SkillFlowTestCase = SkillFlowTestCase.root_bot_only,
        enabled_trace=False,
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
            ),
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
                    MainDialog.skill_bot_id
                )  # AuthenticationConstants.AudienceClaim
                claims_identity.claims[
                    "azp"
                ] = (
                    MainDialog.parent_bot_id
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
                        None, MainDialog.parent_bot_id
                    )

            async def aux(
                turn_context: TurnContext,  # pylint: disable=unused-argument
                activities: List[Activity],
                next: Callable,
            ):
                for activity in activities:
                    if activity.type == ActivityTypes.end_of_conversation:
                        MainDialog.eoc_sent = activity
                        break

                return await next()

            # Interceptor to capture the EoC activity if it was sent so we can assert it in the tests.
            context.on_send_activities(aux)

            MainDialog.dm_turn_result = await dialog_manager.on_turn(context)

        adapter = TestAdapter(logic, activity, enabled_trace)
        adapter.use(AutoSaveStateMiddleware([user_state, conversation_state]))

        return adapter

    async def intro_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            await step_context.context.send_activity(
                MessageFactory.text(
                    "NOTE: LUIS is not configured. To enable all capabilities, add 'LuisAppId', 'LuisAPIKey' and "
                    "'LuisAPIHostName' to the appsettings.json file.",
                    input_hint=InputHints.ignoring_input,
                )
            )

            return await step_context.next(None)
        message_text = (
            str(step_context.options)
            if step_context.options
            else "What can I help you with today?"
        )
        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        return await step_context.prompt(
            TextPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

### partie à modifier pour luis
    async def act_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            # LUIS is not configured, we just run the BookingDialog path with an empty BookingDetailsInstance.
            return await step_context.begin_dialog(
                self._booking_dialog_id, UserProfileDialog()
            )

        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        intent, luis_result = await LuisHelper.execute_luis_query(
            self._luis_recognizer, step_context.context
        )

        if len(intent)>0 and luis_result:
            # Show a warning for Origin and Destination if we can't resolve them.
            await MainDialog._show_warning_for_unsupported_cities(
                step_context.context, luis_result
            )

            # Run the BookingDialog giving it whatever details we have from the LUIS call.
            return await step_context.begin_dialog(self._booking_dialog_id, luis_result)

        else:
            didnt_understand_text = (
                "Sorry, I didn't get that. Please try asking in a different way"
            )
            didnt_understand_message = MessageFactory.text(
                didnt_understand_text, didnt_understand_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(didnt_understand_message)

        return await step_context.next(None)

### summary
    async def recap_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # If the child dialog ("BookingDialog") was cancelled or the user failed to confirm,
        # the Result here will be null.
        if step_context.result is not None:
            result = step_context.result

            # Now we have all the booking details call the booking service.

            # If the call to the booking service was successful tell the user.
            # time_property = Timex(result.travel_date)
            # travel_date_msg = time_property.to_natural_language(datetime.now())
            if result.travel_date_end:
                msg_txt = f"I have you booked to {result.destination} from {result.origin} on {result.travel_date_str} and {result.travel_date_end}, about {result.budget}"
                message = MessageFactory.text(msg_txt, msg_txt, InputHints.ignoring_input)
                await step_context.context.send_activity(message)

            else:
                msg_txt = f"I have you booked to {result.destination} from {result.origin} on {result.travel_date_str}, about {result.budget}"
                message = MessageFactory.text(msg_txt, msg_txt, InputHints.ignoring_input)
                await step_context.context.send_activity(message)

            # WaterfallStep always finishes with the end of the Waterfall or
            # with another dialog; here it is a Prompt Dialog.
            return await step_context.prompt(
                ConfirmPrompt.__name__,
                PromptOptions(prompt=MessageFactory.text("Is this ok?")),
            )
        

    async def final_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        print("info", step_context.result)
        #yes
        if step_context.result==True:
            MainDialog.log_confirm()
            # WaterfallStep always finishes with the end of the Waterfall or
            # with another dialog; here it is a Prompt Dialog.
            prompt_message = "What else can I do for you?"
            return await step_context.replace_dialog(self.id, prompt_message)
        # no
        else:
            MainDialog.log_notconfirm()
            prompt_message = "What else can I do for you?"
            return await step_context.replace_dialog(self.id, prompt_message)


    @staticmethod
    async def _show_warning_for_unsupported_cities(
        context: TurnContext, luis_result: UserProfileDialog
    ) -> None:
        """
        Shows a warning if the requested From or To cities are recognized as entities but they are not in the Airport entity list.
        In some cases LUIS will recognize the From and To composite entities as a valid cities but the From and To Airport values
        will be empty if those entity values can't be mapped to a canonical item in the Airport.
        """
        if luis_result.unsupported_airports:
            message_text = (
                f"Sorry but the following airports are not supported:"
                f" {', '.join(luis_result.unsupported_airports)}"
            )
            message = MessageFactory.text(
                message_text, message_text, InputHints.ignoring_input
            )
            await context.send_activity(message)

    @staticmethod
    def log_notconfirm():
        logger = logging.getLogger(__name__)
        logger.addHandler(AzureEventHandler(connection_string=f'InstrumentationKey={CONFIG.APPINSIGHTS_INSTRUMENTATION_KEY}'))
        logger.setLevel(logging.INFO)
        logger.info('0 - Bot recap not confirmed by user')

    @staticmethod
    def log_confirm():
        logger = logging.getLogger(__name__)
        logger.addHandler(AzureEventHandler(connection_string=f'InstrumentationKey={CONFIG.APPINSIGHTS_INSTRUMENTATION_KEY}'))
        logger.setLevel(logging.INFO)
        logger.info('1 - Bot recap confirmed by user')

    
