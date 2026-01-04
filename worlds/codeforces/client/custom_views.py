from math import floor
from typing import Any, TYPE_CHECKING

from kivy.animation import Animation
from kivy.core.window import Keyboard, Window
from kivy.properties import StringProperty, ObjectProperty, NumericProperty, BooleanProperty
from kivy.input import MotionEvent
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.button import MDIconButton
from kivymd.uix.recycleview import MDRecycleView

from Utils import open_file

from ..game.game import ProblemStatus, Game

if TYPE_CHECKING:
    from .codeforces_client import CodeforcesContext


class CodeforcesGameView(MDRecycleView):
    notif_text = StringProperty("Test Notif")
    notif_pos = NumericProperty(0)

    _keyboard: Keyboard | None = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.bind_keyboard()

    def on_touch_down(self, touch: MotionEvent) -> None:
        self.bind_keyboard()
        return super().on_touch_down(touch)

    def bind_keyboard(self) -> None:
        if self._keyboard is not None:
            return
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

    def _keyboard_closed(self) -> None:
        if self._keyboard is None:
            return
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, _: Any, keycode: tuple[int, str], _1: Any, _2: Any) -> bool:
        return True


class CodeforcesProblemHeader(BoxLayout):
    pass


class CodeforcesConfigButton(MDIconButton):
    context_reference: "CodeforcesContext" = None

    handle_present = BooleanProperty(False)
    api_present = BooleanProperty(False)
    refreshing = BooleanProperty(False)

    _rotation = NumericProperty(0)
    _spin_anim = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            handle_present=self._update_icon,
            api_present=self._update_icon,
            refreshing=self._update_icon,
        )
        self.bind(
            refreshing=self.on_refreshing,
        )

        self.bind(on_release=self.on_release)

    def on_refreshing(self, instance, value):
        if value:
            self.start_spin()
        else:
            self.stop_spin()

    def start_spin(self):
        if self._spin_anim:
            return
        # Opacity will never actually hit 0.3 - after 0.5 seconds lag anyways.
        self._spin_anim = Animation(_rotation=-360, duration=0.8) & Animation(opacity=0.3, duration=0.8)
        self._spin_anim.bind(on_complete=self._loop_spin)
        self._spin_anim.start(self)

    def _loop_spin(self, *args):
        self._rotation = 0
        self.opacity = 1
        if self.refreshing:
            self._spin_anim.start(self)
        else:
            self._spin_anim = None

    def stop_spin(self):
        if self._spin_anim:
            self._spin_anim.cancel(self)
            self._spin_anim = None
        self._rotation = 0

    def on_release(self, *args):
        open_file(self.context_reference.get_yaml_path())

    def _update_icon(self, *args):
        self.icon = self.get_icon()

    def get_icon(self):
        if self.refreshing:
            return "refresh"
        if not self.handle_present:
            return "file-alert"
        if not self.api_present:
            return "file-account"
        return "file-cog"


class CodeforcesProblemTopBoxes(MDRecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []

    def set_problem_info(self, problem_data: dict[str, Any], problem_status: list[ProblemStatus]):
        new_data = []
        for i in range(len(problem_status)):
            new_data.append(
                {
                    "problem_name": problem_data[i]["name"],
                    "problem_url": problem_data[i]["url"],
                    "problem_state": problem_status[i].name,
                    "problem_idx": i + 1,
                }
            )
        self.data = new_data


class CodeforcesPreview(RecycleDataViewBehavior, Image):
    COLOR_HIDDEN = (0.6, 0.6, 0.6, 0.4)
    COLOR_FULL_SOLVE = (0, 1, 0, 0.8)
    COLOR_AVAILABLE = (0.8, 0.8, 0.8, 0.6)
    COLOR_CLEARED = (0.3, 0.3, 0.8, 0.4)
    COLOR_CLEARED_HIDDEN = (0.2, 0.2, 0.6, 0.2)

    index = None

    problem_idx = NumericProperty(-1)
    problem_state = StringProperty("")
    problem_name = StringProperty("")
    problem_url = StringProperty("")

    def __init__(self, fit_mode="fill", **kwargs):
        super().__init__(fit_mode=fit_mode, **kwargs)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        val = super().refresh_view_attrs(rv, index, data)
        self.color = self.get_color()
        return val

    def get_color(self):
        if self.problem_state == ProblemStatus.AVAILABLE.name:
            return self.COLOR_AVAILABLE
        elif self.problem_state == ProblemStatus.FULL_SOLVED.name:
            return self.COLOR_FULL_SOLVE
        elif self.problem_state == ProblemStatus.HIDDEN.name:
            return self.COLOR_HIDDEN
        elif self.problem_state == ProblemStatus.CLEARED.name:
            return self.COLOR_CLEARED
        elif self.problem_state == ProblemStatus.CLEARED_HIDDEN.name:
            return self.COLOR_CLEARED_HIDDEN
        return self.COLOR_HIDDEN


class CodeforcesProblemBox(MDRecycleView):
    game_reference: Game = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []

    def set_problem_info(self, problem_data: dict[str, Any], problem_status: list[ProblemStatus]):
        new_data = []
        for i in range(len(problem_status)):
            new_data.append(
                {
                    "problem_name": problem_data[i]["name"],
                    "problem_url": problem_data[i]["url"],
                    "problem_state": problem_status[i].name,
                    "problem_idx": i + 1,
                }
            )
        self.data = new_data

    def check_resize(self, _: int, _1: int) -> None:
        parent_width, parent_height = self.parent.size
        self.size = parent_width, parent_height - 86


class CodeforcesLabel(RecycleDataViewBehavior, BoxLayout):
    index = None

    rv = ObjectProperty(None)

    problem_idx = NumericProperty(-1)
    problem_state = StringProperty("")
    problem_name = StringProperty("")
    problem_url = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        self.rv = rv
        self.index = index
        return super().refresh_view_attrs(rv, index, data)


class CodeforcesUpgradeList(BoxLayout):
    memory_val = StringProperty("1000")
    time_mult = NumericProperty(1)
    memory_string = StringProperty("1KB")

    def __init__(self):
        super().__init__()

        def on_change(inst, val):
            inst.memory_string = inst.calc_memory_string(val)
            # Trigger to begin

        on_change(self, self.memory_val)
        self.bind(memory_val=on_change)

    def calc_memory_string(self, val):
        try:
            m = int(val)
            if m < 1000:
                return f"{m}B"
            return f"{floor(m / 1000)}KB"
        except:
            if val == "inf":
                return "∞"
            return "Unknown"
