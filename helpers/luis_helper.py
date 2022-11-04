# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from enum import Enum
import urllib
import json
import requests
from typing import Dict
from botbuilder.ai.luis import LuisRecognizer
from botbuilder.core import IntentScore, TopIntent, TurnContext
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from msrest.authentication import CognitiveServicesCredentials
from user_profile import UserProfile
from datetime import datetime
from config import DefaultConfig

CONFIG = DefaultConfig()

class Intent(Enum):
    BOOK_FLIGHT = "bookFlight"

class SubEntities(Enum):
    DST_CITY = "dst_city"
    OR_CITY = "or_city"
    STR_DATE = "str_date"
    END_DATE = "end_date"
    BUDGET = "budget"
    START_DATE_FT = "start"
    END_DATE_FT = "end"


def top_intent(intents: Dict[Intent, dict]) -> TopIntent:
    max_intent = Intent.NONE_INTENT
    max_value = 0.0

    for intent, value in intents:
        intent_score = IntentScore(value)
        if intent_score.score > max_value:
            max_intent, max_value = intent, intent_score.score

    return TopIntent(max_intent, max_value)


class LuisHelper:
    @staticmethod
    def on_prediction(text):
        query_base = (
        f"{CONFIG.LUIS_API_HOST_NAME}/luis/prediction/v3.0/apps/{CONFIG.LUIS_APP_ID}"
        f"/slots/production/predict?verbose=true&show-all-intents=true&log=true"
        f"&subscription-key={CONFIG.LUIS_AUTHORING_KEY}&query="
        )
        query = text

        r = requests.get(query_base + urllib.parse.quote_plus(query))
        print("---", r.text)
        res = json.loads(r.text)
        return res


    @staticmethod
    async def execute_luis_query(
        luis_recognizer: LuisRecognizer, turn_context: TurnContext
    ) -> (Intent, object):
        """
        Returns an object with preformatted LUIS results for the bot's dialogs to consume.
        """
        result = None
        intent = None

        try:
            
            recognizer_result = LuisHelper.on_prediction(turn_context.activity.text)
            intent = recognizer_result["prediction"]["intents"]["bookFlight"]
            if len(intent)>0:
                result = UserProfile()
                # We need to get the result from the LUIS JSON which at every level returns an array.
                to_entities = recognizer_result["prediction"]["entities"]
                if len(to_entities) > 0:
                    
                    element = to_entities.get("Book Flight", [{"$instance": {}}])[0][
                        "$instance"
                    ]
                    if SubEntities.DST_CITY.value in element:
                        result.destination = element[SubEntities.DST_CITY.value][0]["text"].capitalize()
                        print("-------ok")
                    else:
                        print("----error")
                        result.unsupported_airports.append(
                            SubEntities.DST_CITY.value
                        )

                    if SubEntities.OR_CITY.value in element:
                        result.origin = element[SubEntities.OR_CITY.value][0]["text"].capitalize()
                        print("-------ok")
                    else:
                        print("----error")
                        result.unsupported_airports.append(
                            SubEntities.OR_CITY.value
                        )

                    if SubEntities.STR_DATE.value in element:
                        print("-------str date")
                        val = to_entities["datetimeV2"][0]["values"][0]["resolution"][0]["start"]
                        val_format = datetime.strptime(val, '%Y-%m-%d').strftime('%m/%d/%Y')
                        result.travel_date_str = val_format
                        print("-------ok")
                    else:
                        print("----error")
                        if "datetimeV2" in to_entities:
                            val = to_entities["datetimeV2"][0]["values"][0]["resolution"][0]
                            if SubEntities.START_DATE_FT.value in val:
                                val = to_entities["datetimeV2"][0]["values"][0]["resolution"][0]["start"]
                                val_format = datetime.strptime(val, '%Y-%m-%d').strftime('%m/%d/%Y')
                                result.travel_date_str = val_format
                            else:
                                result.unsupported_airports.append(
                                    SubEntities.STR_DATE.value)
                        else:
                            result.unsupported_airports.append(
                                    SubEntities.STR_DATE.value)

                    if SubEntities.END_DATE.value in element:
                        print("-------end date")
                        val = to_entities["datetimeV2"][0]["values"][0]["resolution"][0]["end"]
                        val_format = datetime.strptime(val, '%Y-%m-%d').strftime('%m/%d/%Y')
                        result.travel_date_end = val_format
                        print("-------ok")
                    else:
                        if "datetimeV2" in to_entities:
                            print("-------end date datetime")
                            val = to_entities["datetimeV2"][0]["values"][0]["resolution"][0]
                            if SubEntities.END_DATE_FT.value in val:
                                val = to_entities["datetimeV2"][0]["values"][0]["resolution"][0]["end"]
                                val_format = datetime.strptime(val, '%Y-%m-%d').strftime('%m/%d/%Y')
                                result.travel_date_end = val_format
                                print("-------end date datetime ok")
                            else: 
                                result.unsupported_airports.append(
                                    SubEntities.END_DATE.value
                                )
                        else:
                            result.unsupported_airports.append(
                                SubEntities.END_DATE.value
                            )

                    if SubEntities.BUDGET.value in element:
                        result.budget = element[SubEntities.BUDGET.value][0]["text"]
                        print("-------ok")
                    else:
                        print("----error")
                        result.unsupported_airports.append(
                            SubEntities.BUDGET.value
                        )


                # This value will be a TIMEX. And we are only interested in a Date so grab the first result and drop
                # the Time part. TIMEX is a format that represents DateTime expressions that include some ambiguity.
                # e.g. missing a Year.
                # date_entities = recognizer_result.entities.get("datetimeV2", [])
                # if date_entities:
                #     timex = date_entities[0]["timex"]

                #     if timex:
                #         datetime = timex[0].split("T")[0]

                #         result.travel_date = datetime

                # else:
                #     result.travel_date = None

        except Exception as exception:
            print(exception)

        return intent, result

if __name__ == '__main__':
    luis = LuisHelper()
