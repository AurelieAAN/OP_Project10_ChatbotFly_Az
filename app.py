from aiohttp.web import Request, Response, json_response
from aiohttp import web
from http import HTTPStatus
from botbuilder.schema import Activity
import asyncio
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState,
    TelemetryLoggerMiddleware,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.applicationinsights import ApplicationInsightsTelemetryClient
from botbuilder.integration.applicationinsights.aiohttp import (
    AiohttpTelemetryProcessor,
    bot_telemetry_middleware,
)
from adapter_with_error_handler import AdapterWithErrorHandler
from config import DefaultConfig 
from bots import DialogBot
from dialogs.main_dialog import MainDialog
from dialogs.user_profile_dialog import UserProfileDialog
from flight_booking_recognizer import FlightBookingRecognizer

#app = Flask(__name__)
loop = asyncio.get_event_loop()

CONFIG = DefaultConfig()
botadaptersettings = BotFrameworkAdapterSettings("", "")
botadapter = BotFrameworkAdapter(botadaptersettings)



# Create MemoryStorage, UserState and ConversationState
MEMORY = MemoryStorage()
USER_STATE = UserState(MEMORY)
CONVERSATION_STATE = ConversationState(MEMORY)


# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
ADAPTER = AdapterWithErrorHandler(botadaptersettings, CONVERSATION_STATE)


# Create telemetry client.
# Note the small 'client_queue_size'.  This is for demonstration purposes.  Larger queue sizes
# result in fewer calls to ApplicationInsights, improving bot performance at the expense of
# less frequent updates.
INSTRUMENTATION_KEY = CONFIG.APPINSIGHTS_INSTRUMENTATION_KEY

TELEMETRY_CLIENT = ApplicationInsightsTelemetryClient(
    INSTRUMENTATION_KEY, telemetry_processor=AiohttpTelemetryProcessor(), client_queue_size=10
)


# Code for enabling activity and personal information logging.
TELEMETRY_LOGGER_MIDDLEWARE = TelemetryLoggerMiddleware(telemetry_client=TELEMETRY_CLIENT, log_personal_information=True)
ADAPTER.use(TELEMETRY_LOGGER_MIDDLEWARE)

# Create dialogs and Bot
RECOGNIZER = FlightBookingRecognizer(CONFIG)
BOOKING_DIALOG = UserProfileDialog(telemetry_client=TELEMETRY_CLIENT)
DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG, telemetry_client=TELEMETRY_CLIENT)
BOT = DialogBot(CONVERSATION_STATE, USER_STATE, DIALOG, TELEMETRY_CLIENT)

async def messages(req: Request) -> Response:
    # Main bot message handler.
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=HTTPStatus.OK)


def init_funct(argv):
    APP = web.Application(middlewares=[bot_telemetry_middleware, aiohttp_error_middleware])
    APP.router.add_post("/api/messages", messages)
    return APP


if __name__ == '__main__':
    APP = init_funct(None)
    try:
        web.run_app(APP, host="localhost", port=3978)
    except Exception as error:
        raise error

