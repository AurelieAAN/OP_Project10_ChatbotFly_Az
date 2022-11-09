# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import sys
sys.path.insert(0, "../")
from datetime import datetime
from sqlite3 import Date
from enum import Enum
import aiounittest
from typing import Callable, List, Tuple
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
from OP_Project10_ChatbotFly_Az.user_profile import UserProfile
from OP_Project10_ChatbotFly_Az.dialogs.user_profile_dialog import UserProfileDialog
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


class UserProfileDialogTests(aiounittest.AsyncTestCase):
    """
    self.beforeEach(() => {
        _dmTurnResult = undefined
    })
    """
    async def test_trace_bot_state(self):
        UserProfileDialog.dm_turn_result = None
        dialog = UserProfileDialog()

        def assert_is_trace(activity, description):  # pylint: disable=unused-argument
            assert activity.type == ActivityTypes.trace

        def assert_is_trace_and_label(activity, description):
            assert_is_trace(activity, description)
            assert activity.label == "Bot State"

        test_flow = await UserProfileDialog.create_test_flow(
            dialog, SkillFlowTestCase.root_bot_only, True
        )

        step1 = await test_flow.send("Hi")
        step2 = await step1.assert_reply("To what city would you like to travel?")
        step3 = await step2.assert_reply(assert_is_trace_and_label)
        step4 = await step3.send("SomeName")
        step5 = await step4.assert_reply("From what city will you be travelling?")
        step6 = await step5.assert_reply(assert_is_trace_and_label)
        step7 = await step6.send("SomeName")
        step8 = await step7.assert_reply("On what date would you like to travel?")
        step9 = await step8.assert_reply(assert_is_trace_and_label)
        step10 = await step9.send("07/08/2022")
        step11 = await step10.assert_reply("I'm sorry, for best results, please enter your travel date including the month, day and year, and it is greater than today")
        step12 = await step11.assert_reply(assert_is_trace_and_label)
        step13 = await step12.send("12/08/2022")
        step14 = await step13.assert_reply("On what date would you like to travel?")
        step15 = await step14.assert_reply(assert_is_trace_and_label)
        step16 = await step15.send("12/09/2022")
        step17 = await step16.assert_reply("Please enter your budget.")
        step18 = await step17.assert_reply(assert_is_trace_and_label)
        step19 = await step18.send("something")
        step20 = await step19.assert_reply("The value entered must be greater than 0 and must be a number.")
        step21 = await step20.assert_reply(assert_is_trace_and_label)
        step22 = await step21.send("2000")


        self.assertEqual(
            UserProfileDialog.dm_turn_result.turn_result.status,
            DialogTurnStatus.Complete,
        )
