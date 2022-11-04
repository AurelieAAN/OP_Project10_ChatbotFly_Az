# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from datetime import date
from botbuilder.schema import Attachment


class UserProfile:
    """
      This is our application state. Just a regular serializable Python class.
    """

    def __init__(
        self,
        destination: str = None,
        origin: str = None,
        travel_date_str: str = None,
        travel_date_end: str = None,
        budget: str = None,
        unsupported_airports=None,
    ):
        if unsupported_airports is None:
            unsupported_airports = []
        self.destination = destination
        self.origin = origin
        self.travel_date_str = travel_date_str
        self.travel_date_end = travel_date_end
        self.budget = budget
        self.unsupported_airports = unsupported_airports