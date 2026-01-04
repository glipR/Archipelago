from enum import Enum
from typing import NamedTuple

from ..items import ID_TO_ITEM_NAME, ITEM_NAME_TO_ID

# Some helper functions to classify items


class RemotelyReceivedItem(NamedTuple):
    remote_item_id: int
    remote_location_id: int
    remote_location_player: int
