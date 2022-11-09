# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import sys



sys.path.insert(0, "../")
from datetime import datetime
from sqlite3 import Date
from enum import Enum
import aiounittest
from typing import Callable, List, Tuple
from OP_Project10_ChatbotFly_Az.flight_booking_recognizer import FlightBookingRecognizer
from OP_Project10_ChatbotFly_Az.dialogs.main_dialog import MainDialog
#from .cancel_and_help_dialog import CancelAndHelpDialog
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

#from helpers.date_resolver_dialog import DateResolverDialog
#from user_profile import UserProfile
from unittest.mock import Mock

import os
import pytest
from user_profile import UserProfile
from dialogs.user_profile_dialog import UserProfileDialog
from unittest import TestCase
from botbuilder.core import (
    TurnContext, 
    ConversationState, 
    MemoryStorage, 
    MessageFactory, 
)
from botbuilder.dialogs.prompts import PromptOptions
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    ChannelAccount,
    ConversationAccount,
    EndOfConversationCodes,
    InputHints,
)
from botbuilder.dialogs import (
    ComponentDialog,
    Dialog,
    DialogContext,
    DialogEvents,
    DialogInstance,
    DialogReason,
    TextPrompt,
    WaterfallDialog,
    DialogManager,
    DialogManagerResult,
    DialogTurnStatus,
    WaterfallStepContext,
)
from botbuilder.core.adapters import TestAdapter
from botframework.connector.auth import AuthenticationConstants, ClaimsIdentity
import pytest
from config import DefaultConfig 
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


class MainDialogTests(aiounittest.AsyncTestCase):
    """
    self.beforeEach(() => {
        _dmTurnResult = undefined
    })
    """
    async def test_trace_bot_state_yes(self):
        MainDialog.dm_turn_result = None
        dialog = MainDialog(FlightBookingRecognizer(CONFIG), UserProfileDialog())

        def assert_is_trace(activity, description):  # pylint: disable=unused-argument
            assert activity.type == ActivityTypes.trace

        def assert_is_trace_and_label(activity, description):
            assert_is_trace(activity, description)
            assert activity.label == "Bot State"

        test_flow = await UserProfileDialog.create_test_flow(
            dialog, SkillFlowTestCase.root_bot_only, True
        )

        step1 = await test_flow.send("Hi")
        step2 = await step1.assert_reply("What can I help you with today?")
        step3 = await step2.assert_reply(assert_is_trace_and_label)
        step4 = await step3.send("from madrid to santos from 4800, on between 12/27/2022 and 01/05/2023")
        step5 = await step4.assert_reply("I have you booked to Santos from Madrid on 12/27/2022 and 01/05/2023, about 4800,")
        step6 = await step5.assert_reply("Is this ok? (1) Yes or (2) No")
        step7 = await step6.assert_reply(assert_is_trace_and_label)
        step8 = await step7.send("yes")
        step9 = await step8.assert_reply("What else can I do for you?")


        self.assertEqual(
            UserProfileDialog.dm_turn_result.turn_result.status,
            DialogTurnStatus.Waiting,
        )

    async def test_trace_bot_state_no(self):
        MainDialog.dm_turn_result = None
        dialog = MainDialog(FlightBookingRecognizer(CONFIG), UserProfileDialog())

        def assert_is_trace(activity, description):  # pylint: disable=unused-argument
            assert activity.type == ActivityTypes.trace

        def assert_is_trace_and_label(activity, description):
            assert_is_trace(activity, description)
            assert activity.label == "Bot State"

        test_flow = await UserProfileDialog.create_test_flow(
            dialog, SkillFlowTestCase.root_bot_only, True
        )

        step1 = await test_flow.send("Hi")
        step2 = await step1.assert_reply("What can I help you with today?")
        step3 = await step2.assert_reply(assert_is_trace_and_label)
        step4 = await step3.send("from madrid to santos from 4800, on between 12/27/2022 and 01/05/2023")
        step5 = await step4.assert_reply("I have you booked to Santos from Madrid on 12/27/2022 and 01/05/2023, about 4800,")
        step6 = await step5.assert_reply("Is this ok? (1) Yes or (2) No")
        step7 = await step6.assert_reply(assert_is_trace_and_label)
        step8 = await step7.send("no")
        step9 = await step8.assert_reply("What else can I do for you?")


        self.assertEqual(
            UserProfileDialog.dm_turn_result.turn_result.status,
            DialogTurnStatus.Waiting,
        )
