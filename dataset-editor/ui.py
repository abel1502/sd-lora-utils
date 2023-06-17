from __future__ import annotations
import typing
from nicegui import ui, globals as ui_globals
import base64
import pathlib
from dataclasses import dataclass, field

from . import dataset


GLOBAL_CSS: typing.Final[str] = """
<style>
    .body--dark .card-changed {
        background-color: #6B3400;
    }

    .body--light .card-changed {
        background-color: #FFEECC;
    }
    
    .body--dark .card-selected {
        background-color: #003E6B;
    }
    
    .body--light .card-selected {
        background-color: #CCE5FF;
    }
</style>
"""


async def toggle_dark(x: typing.Any) -> None:
    js_value = str(x.value).lower()
    await ui_globals.get_client().connected()
    await ui.run_javascript(f'Quasar.Dark.set({js_value})', respond=False)


async def scroll_top():
    await ui_globals.get_client().connected()
    await ui.run_javascript("window.scrollTo(0, 0)", respond=False)


def to_base64(path: str | pathlib.Path, picname: str) -> str:
    if isinstance(path, str):
        path = pathlib.Path(path)

    return 'data:image/png;base64, {}'.format(
        base64.b64encode((path / picname).read_bytes()).decode('utf-8')
    )


def split_tags(text: str) -> list[str]:
    return [x for x in map(str.strip, text.split(',')) if x]


@dataclass
class UIDatasetItem(dataset.DatasetItem):
    card: ui.card | None = None
    prev_tags_label: ui.markdown | None = None
    input_field: ui.textarea | None = None
    
    def __post_init__(self) -> None:
        self.card = ui.card().classes('max-w-md')
        
        with self.card:
            ui.image(self.img_file).props('fit=scale-down').style('max-width: 100%, max-height: 100%')
            
            with ui.card_section():
                ui.checkbox(f"{self.img_file.name}", on_change=lambda x: self.select_set(x.value)) \
                    .bind_value_from(self, 'selected')
                self.prev_tags_label = ui.markdown("")
                self.input_field = ui.textarea('Tags')
                ui.button('Update', on_click=lambda _: self.update_from_input(self.input_field.value))
        
        return super().__post_init__()
    
    def on_reset(self) -> None:
        super().on_reset()
        
        self.prev_tags_label.set_content(f"**Stored tags:**\n\n{self.tags_str}")
        self.input_field.value = self.tags_str

    def on_changed(self) -> None:
        super().on_changed()
        
        self.input_field.value = self.tags_str
        self.update_style()
    
    def on_selected(self, state: bool) -> None:
        super().on_selected(state)
        
        self.update_style()
    
    def update_style(self) -> None:
        def _add_or_remove(cls: str, state: bool) -> None:
            if state:
                self.card.classes(add=cls)
            else:
                self.card.classes(remove=cls)
        
        _add_or_remove('card-changed', self.dirty)
        _add_or_remove('card-selected', self.selected)

    @property
    def tags_str(self) -> str:
        return ', '.join(self.tags) + ','
    
    def update_from_input(self, text: str) -> None:
        self.set_tags(split_tags(text))


@dataclass
class UIDataset(dataset.Dataset):
    ITEM_CLS: typing.ClassVar[typing.Type[UIDatasetItem]] = UIDatasetItem
    
    ui_input_A: ui.input | None = None
    ui_input_B: ui.input | None = None
    ui_affect_all: ui.checkbox | None = None
    ui_persist_inputs: ui.checkbox | None = None
    
    @classmethod
    def setup(
        cls,
        path: str | pathlib.Path,
        controls: ui.row,
        table: ui.table,
    ) -> UIDataset:
        if isinstance(path, str):
            path = pathlib.Path(path)
        
        controls.clear()
        table.clear()
        
        self = cls(path)
    
        with controls:
            self.add_controls()

        with table:
            self.read()
        
        return self
    
    def add_controls(self) -> None:
        with ui.column().style('width: 90%'):
            self._add_inputs()
        
            self._add_select_buttons()
        
            self._add_op_buttons()

    def _apply_op(
        self,
        func: typing.Callable[[UIDatasetItem], typing.Any],
        *args,
        **kwargs,
    ) -> None:
        applier = self.for_selected
        
        if self.ui_affect_all.value:
            applier = self.for_all
        
        applier(func, *args, **kwargs)
        
        if not self.ui_persist_inputs.value:
            self.ui_input_A.value = ""
            self.ui_input_B.value = ""
            self.ui_affect_all.value = False

    def _input_tags(self, field: typing.Literal['A', 'B'] = 'A') -> list[str]:
        assert field in ('A', 'B'), f"Invalid field {field!r}"
        
        return split_tags(getattr(self, f'ui_input_{field}').value)

    def _add_inputs(self) -> None:
        with ui.row().classes('w-full'):
            # Two common input fields. Should be as wide as possible
            self.ui_input_A = ui.input('A').style('min-width: 600px')  # .style('width: 45%')
            self.ui_input_B = ui.input('B').style('min-width: 600px')  # .style('width: 45%')

    def _add_select_buttons(self) -> None:
        with ui.row():
            ui.button("Select all", on_click=lambda: self.select_all())
            ui.button("Reset selection", on_click=lambda: self.select_none())
            ui.button("Invert selection", on_click=lambda: self.select_invert())
            self.ui_affect_all = ui.checkbox("Affect everything")
            self.ui_persist_inputs = ui.checkbox("Persist inputs")

    def _add_op_buttons(self) -> None:
        with ui.row():
            self._add_unary_buttons()
            
            self._add_binary_buttons()
            
            self._add_special_buttons()
    
    def _add_unary_buttons(self) -> None:
        ui.button(
            "Prepend A",
            on_click=lambda: self._apply_op(
                UIDatasetItem.prepend_tags,
                self._input_tags('A'),
            )
        )
        ui.button(
            "Add A",
            on_click=lambda: self._apply_op(
                UIDatasetItem.add_tags,
                self._input_tags('A'),
            )
        )
        ui.button(
            "Remove A",
            on_click=lambda: self._apply_op(
                UIDatasetItem.remove_tags,
                self._input_tags('A'),
            )
        )
    
    def _add_binary_buttons(self) -> None:
        ui.button(
            "Replace A with B",
            on_click=lambda: self._apply_op(
                UIDatasetItem.replace_tags,
                self._input_tags('A'),
                self._input_tags('B'),
            )
        )

    def _add_special_buttons(self) -> None:
        ui.button(
            "Autotag",
            on_click=lambda: ui.notify('Not implemented yet!', type='info'),
            color='purple',
        )
        ui.button(
            "Remove duplicates",
            on_click=lambda: ui.notify('Not implemented yet!', type='info'),
            color='purple',
        )


def run_ui(
    port: int | None = None,
    dataset_path: str | pathlib.Path | None = None,
    show: bool = False,
    dark_mode: bool = False,
) -> None:

    ui.add_head_html(GLOBAL_CSS)
    
    ui.switch("Toggle dark mode", on_change=toggle_dark).set_value(dark_mode)
    
    with ui.row():
        dataset_path_field = ui.input("Dataset path", placeholder="C:\\Users\\User\\datasets\\dataset1").style("min-width: 600px")
        # TODO: Allow picking the tag file extension as well?
        dataset_path_btn = ui.button("Load dataset").props("size=lg")
        dataset_save_btn = ui.button("Save to disk", color='orange').props("size=lg")

    dataset_controls = ui.row().classes('w-full justify-between')
    table = ui.row().classes('w-full')
    
    def load_dataset() -> None:
        ds = UIDataset.setup(dataset_path_field.value, dataset_controls, table)
        
        dataset_save_btn.on(
            "click",
            lambda _: ds.flush(),
        )

    dataset_path_btn.on(
        "click",
        lambda _: load_dataset(),
    )

    with ui.page_sticky():
        ui.button("Scroll to the top", on_click=scroll_top)
    
    if dataset_path:
        dataset_path_field.value = str(dataset_path)
        load_dataset()
    
    ui.run(
        title="Dataset Tag Editor",
        port=port or 8080,
        reload=False,
        show=show,
    )


__all__ = [
    "run_ui",
]
