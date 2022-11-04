# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from .cancel_and_help_dialog import CancelAndHelpDialog
from datatypes_date_time.timex import Timex
from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
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
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from botbuilder.core import MessageFactory, UserState
from helpers.date_resolver_dialog import DateResolverDialog
from user_profile import UserProfile


class UserProfileDialog(CancelAndHelpDialog):
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
                    #self.summary_step,
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

    async def destination_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        # WaterfallStep always finishes with the end of the Waterfall or with another dialog;
        # here it is a Prompt Dialog. Running a prompt here means the next WaterfallStep will
        # be run when the users response is received.
        booking_details = step_context.options

        if booking_details.destination is None:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("To what city would you like to travel?")
                ),
            )
        return await step_context.next(booking_details.destination)


    async def origin_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for origin city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.destination = step_context.result
        if booking_details.origin is None:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("From what city will you be travelling?")
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.origin)

    async def travel_date_str_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
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

        # Capture the results of the previous step
        booking_details.travel_date_str = step_context.result

        if not booking_details.travel_date_end or self.is_ambiguous(
            booking_details.travel_date_end
        ):
            return await step_context.begin_dialog(
                DateResolverDialog.__name__, booking_details.travel_date_end
            )  # pylint: disable=line-too-long

        return await step_context.next(booking_details.travel_date_end)

    async def name_confirm_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        step_context.values["name"] = step_context.result

        # We can send messages to the user at any point in the WaterfallStep.
        await step_context.context.send_activity(
            MessageFactory.text(f"Thanks {step_context.result}")
        )

        # WaterfallStep always finishes with the end of the Waterfall or
        # with another dialog; here it is a Prompt Dialog.
        return await step_context.prompt(
            ConfirmPrompt.__name__,
            PromptOptions(
                prompt=MessageFactory.text("Would you like to give your age?")
            ),
        )

    async def budget_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # User said "yes" so we will be prompting for the age.
        # WaterfallStep always finishes with the end of the Waterfall or with another dialog,
        # here it is a Prompt Dialog.
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.travel_date_end = step_context.result
        if booking_details.budget is None:
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("Please enter your budget."),
                    retry_prompt=MessageFactory.text(
                        "The value entered must be greater than 0"
                    ),
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.budget)

    async def picture_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        age = step_context.result
        step_context.values["age"] = age

        msg = (
            "No age given."
            if step_context.result == -1
            else f"I have your age as {age}."
        )

        # We can send messages to the user at any point in the WaterfallStep.
        await step_context.context.send_activity(MessageFactory.text(msg))

        if step_context.context.activity.channel_id == "msteams":
            # This attachment prompt example is not designed to work for Teams attachments, so skip it in this case
            await step_context.context.send_activity(
                "Skipping attachment prompt in Teams channel..."
            )
            return await step_context.next(None)

        # WaterfallStep always finishes with the end of the Waterfall or with another dialog; here it is a Prompt
        # Dialog.
        prompt_options = PromptOptions(
            prompt=MessageFactory.text(
                "Please attach a profile picture (or type any message to skip)."
            ),
            retry_prompt=MessageFactory.text(
                "The attachment must be a jpeg/png image file."
            ),
        )
        return await step_context.prompt(AttachmentPrompt.__name__, prompt_options)

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

    async def summary_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        if step_context.result:
            # Get the current profile object from user state.  Changes to it
            # will saved during Bot.on_turn.
            user_profile = await self.user_profile_accessor.get(
                step_context.context, UserProfile
            )

            user_profile.transport = step_context.values["transport"]
            user_profile.name = step_context.values["name"]
            user_profile.age = step_context.values["age"]
            user_profile.picture = step_context.values["picture"]

            msg = f"I have your mode of transport as {user_profile.transport} and your name as {user_profile.name}."
            if user_profile.age != -1:
                msg += f" And age as {user_profile.age}."

            await step_context.context.send_activity(MessageFactory.text(msg))

            if user_profile.picture:
                await step_context.context.send_activity(
                    MessageFactory.attachment(
                        user_profile.picture, "This is your profile picture."
                    )
                )
            else:
                await step_context.context.send_activity(
                    "A profile picture was saved but could not be displayed here."
                )
        else:
            await step_context.context.send_activity(
                MessageFactory.text("Thanks. Your profile will not be kept.")
            )

        # WaterfallStep always finishes with the end of the Waterfall or with another
        # dialog, here it is the end.
        return await step_context.end_dialog()


    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        if step_context.result:
            booking_details = step_context.options
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
