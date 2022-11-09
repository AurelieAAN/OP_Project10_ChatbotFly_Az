# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import sys
sys.path.insert(0, "../")
from enum import Enum
import urllib
import json
import requests
import aiounittest
from typing import Dict
from botbuilder.ai.luis import LuisRecognizer
from botbuilder.core import IntentScore, TopIntent, TurnContext
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from msrest.authentication import CognitiveServicesCredentials
from OP_Project10_ChatbotFly_Az.user_profile import UserProfile
from OP_Project10_ChatbotFly_Az.helpers.luis_helper import LuisHelper
from datetime import datetime
from config import DefaultConfig


class LuisHelperTest(aiounittest.AsyncTestCase):

    def test_on_prediction_return_value(self):
        res = LuisHelper().on_prediction("from madrid to santos from 4800, on between 12/27/2022 and 01/05/2023")
        assert res

    def test_on_prediction_return_empty(self):
        res = LuisHelper().on_prediction("from")
        assert res