from __future__ import annotations
import typing
from nicegui import ui
import base64
import pathlib
from dataclasses import dataclass, field

from . import dataset


async def toggle_dark(x: typing.Any) -> None:
    js_value = str(x.value).lower()
    await ui.run_javascript(f'Quasar.Dark.set({js_value})', respond=False)


async def scroll_top():
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
                ui.checkbox(f"{self.img_file.name}").bind_value(self, 'selected')
                self.prev_tags_label = ui.markdown("")
                self.input_field = ui.textarea('Tags')
                ui.button('Update', on_click=lambda _: self.update_from_input(self.input_field.value))
        
        return super().__post_init__()
    
    def on_reset(self) -> None:
        super().on_reset()
        
        self.prev_tags_label.set_content(f"**Stored tags:**\n\n{self.tags_str}")
        self.input_field.value = self.tags_str
        self.card.classes(remove='card-changed')

    def on_changed(self) -> None:
        super().on_changed()
        
        self.input_field.value = self.tags_str
        self.card.classes('card-changed')

    @property
    def tags_str(self) -> str:
        return ', '.join(self.tags) + ','
    
    def update_from_input(self, text: str) -> None:
        self.set_tags(split_tags(text))


class UIDataset(dataset.Dataset):
    ITEM_CLS: typing.ClassVar[typing.Type[UIDatasetItem]] = UIDatasetItem
    
    def notify_of_unsaved_changes(self):
        cnt: int = self.unsaved_changes_cnt
        
        if cnt > 0:
            ui.notify(f'{cnt} unsaved changes')
    
    @classmethod
    def setup(
        cls,
        path: str | pathlib.Path,
        controls: ui.row,
        table: ui.table,
    ) -> None:
        if isinstance(path, str):
            path = pathlib.Path(path)
        
        controls.clear()
        table.clear()
        
        self = cls(path)
    
        with controls:
            self.add_controls()

        with table:
            self.read()
    
    def add_controls(self) -> None:
        with ui.column():
            ui.button('Select all', on_click=lambda: self.select_all())
            ui.button('Reset selection', on_click=lambda: self.select_none())
            ui.button('Invert selection', on_click=lambda: self.select_invert())
        
        with ui.column():
            selection_only_flag = ui.switch('Affect selection only', value=True).style('margin: auto')

            def _applier() -> typing.Callable[..., None]:
                return self.for_selected if selection_only_flag.value else self.for_all
            
            with ui.row():
                with ui.column():
                    tags_input = ui.input('Tags')
                    
                    with ui.row():
                        ui.button(
                            'Prepend',
                            on_click=lambda: _applier()(UIDatasetItem.prepend_tags, split_tags(tags_input.value))
                        )
                        ui.button(
                            'Add',
                            on_click=lambda: _applier()(UIDatasetItem.add_tags, split_tags(tags_input.value))
                        )
                        ui.button(
                            'Remove',
                            on_click=lambda: _applier()(UIDatasetItem.remove_tags, split_tags(tags_input.value))
                        )
        
                ui.splitter()
                
                with ui.column():
                    with ui.row():
                        search = ui.input('Search for')
                        replace = ui.input('Replace with')
                    
                    ui.button(
                        'Replace',
                        on_click=lambda: _applier()(UIDatasetItem.replace_tags, search.value, replace.value)
                    )
        
        # Note: would also require refreshing the dataset; probably should be moved to the initialization instead
        # with ui.column():
        #     ui.label('Save captions as')
        #     ui.select([".txt",".caption"]).bind_value(self, 'tags_file_ext').style('min_width: 150px')
        
        ui.button('Save to disk', on_click=lambda: self.flush()).props('color=orange').props('size=xl')


def run_ui(
    port: int | None = None,
    dataset_path: str | pathlib.Path | None = None,
    show: bool = False,
) -> None:

    ui.add_head_html("""
        <style>
        .body--dark .card-changed {
            background-color: #6B3400;
        }

        .body--light .card-changed {
            background-color: #FFEECC;
        }
        </style>
    """)
    
    ui.switch('Toggle dark mode', on_change=toggle_dark)
    
    with ui.row():
        dataset_path_field = ui.input('Dataset path', placeholder="C:\\Users\\User\\datasets\\dataset1").style('min-width: 600px')
        dataset_path_btn = ui.button('Load dataset')

    # with ui.footer():  # does not work with mobile but nice idea on pc tho
    dataset_controls = ui.row().classes('w-full justify-between')
    
    table = ui.row().classes('w-full')

    dataset_path_btn.on(
        "click",
        lambda _: UIDataset.setup(
            dataset_path_field.value, dataset_controls, table
        )
    )

    with ui.page_sticky():
        ui.button('Scroll to the top', on_click=scroll_top)
    
    if dataset_path:
        dataset_path_field.value = str(dataset_path)
        UIDataset.setup(dataset_path, dataset_controls, table)
    
    ui.run(
        title="Dataset Tag Editor",
        port=port or 8080,
        reload=False,
        show=show,
    )


__all__ = [
    "run_ui",
]
