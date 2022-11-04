#!/usr/bin/env python
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Configuration for the bot."""

import os
from dotenv import load_dotenv
import sys
import argparse
import warnings
warnings.filterwarnings("ignore")

# chargement des variables d'environnment
load_dotenv() 

class DefaultConfig:
    """Configuration for the bot."""

    PORT = 3978
    APP_ID = os.getenv('BOT_APP_ID')
    APP_PASSWORD = os.getenv('BOT_INFO')
    LUIS_AUTHORING_KEY = os.getenv('LUIS_AUTHORING_KEY')
    LUIS_APP_ID = os.getenv('APP_ID')
    LUIS_API_KEY = os.getenv('PREDICTION_KEY')
    # LUIS endpoint host name, ie "westus.api.cognitive.microsoft.com"
    LUIS_API_HOST_NAME = os.getenv('PREDICTION_ENDPOINT')
    APPINSIGHTS_INSTRUMENTATION_KEY = os.getenv('APP_INSIGHT')