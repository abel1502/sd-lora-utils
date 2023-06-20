from __future__ import annotations
import typing
from nicegui import ui, globals as ui_globals
import base64
import pathlib
from dataclasses import dataclass, field
import asyncio
import contextlib

from . import dataset
from .kohya_runner import run_kohya, run_kohya_async
from .local_file_picker import local_file_picker


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
    
    .no-bootom-margin > p {
        margin-bottom: 0 !important;
    }
</style>
"""

KOHYA_PATH: pathlib.Path | None = None


async def toggle_dark(x: typing.Any) -> None:
    js_value = str(x.value).lower()
    await ui_globals.get_client().connected()
    await ui.run_javascript(f'Quasar.Dark.set({js_value})', respond=False)


async def scroll_top() -> None:
    await ui_globals.get_client().connected()
    await ui.run_javascript("window.scrollTo(0, 0)", respond=False)


def to_base64(path: str | pathlib.Path, picname: str) -> str:
    if isinstance(path, str):
        path = pathlib.Path(path)

    return 'data:image/png;base64, {}'.format(
        base64.b64encode((path / picname).read_bytes()).decode('utf-8')
    )


def labeled_slider(
    name: str,
    *,
    min: float = 0.0,
    max: float = 1.0,
    step: float = 0.01,
    value: float | None = None,
    on_change: typing.Callable[[float], None] | None = None,
) -> ui.slider:
    with ui.column():
        label = ui.markdown("")
        slider = ui.slider(min=min, max=max, step=step, value=value, on_change=on_change)\
            .bind_value_to(label, "content", lambda x: f"{name}: **{x:.2f}**")
    
    return slider


def remove_tags_underscores(tags: typing.Sequence[str]) -> list[str]:
    # TODO: Maybe not ignore short tags?
    return [tag.replace('_', ' ') if len(tag) > 3 else tag for tag in tags]


@dataclass
class UIDatasetItem(dataset.DatasetItem):
    card: ui.card | None = None
    prev_tags_label: ui.markdown | None = None
    selected_field: ui.checkbox | None = None
    input_field: ui.textarea | None = None
    
    def __post_init__(self) -> None:
        self.card = ui.card().classes('max-w-md')
        
        with self.card:
            ui.image(self.img_file).props('fit=scale-down').style('max-width: 100%, max-height: 100%')
            
            with ui.card_section():
                self.selected_field = ui.checkbox(f"{self.img_file.name}", on_change=lambda x: self.select_set(x.value))
                self.prev_tags_label = ui.markdown("")
                self.input_field = ui.textarea('Tags')
                ui.button('Update', on_click=lambda _: self.update_from_input(self.input_field.value))
        
        return super().__post_init__()
    
    def on_reset(self) -> None:
        super().on_reset()
        
        self.prev_tags_label.set_content(f"**Stored tags:**\n\n{self.tags_str}")
        self.input_field.value = self.tags_str
        self.update_style()

    def on_changed(self) -> None:
        super().on_changed()
        
        self.input_field.value = self.tags_str
        self.update_style()
    
    def on_selected(self, state: bool) -> None:
        self.parent.selected_cnt += state - self.selected
        
        super().on_selected(state)
        
        self.selected_field.value = state
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
        return dataset.join_tags(self.tags, trailing_comma=True)
    
    def update_from_input(self, text: str) -> None:
        self.set_tags(dataset.split_tags(text))


@dataclass
class UIDataset(dataset.Dataset):
    ITEM_CLS: typing.ClassVar[typing.Type[UIDatasetItem]] = UIDatasetItem
    
    selected_cnt: int = 0
    
    ui_controls: ui.row | None = None
    ui_table: ui.table | None = None
    ui_input_A: ui.input | None = None
    ui_input_B: ui.input | None = None
    ui_affect_all: ui.checkbox | None = None
    ui_persist_inputs: ui.checkbox | None = None
    
    ui_loading_dialog: ui.dialog | None = None
    ui_autotag_dialog: ui.dialog | None = None
    ui_find_duplicates_dialog: ui.dialog | None = None
    
    
    def setup(
        self,
        controls: ui.row,
        table: ui.table,
    ) -> UIDataset:
        self.ui_controls = controls
        self.ui_table = table
        
        self.setup_cached_dialogs()
        
        controls.clear()
        
        with controls:
            self.add_controls()

        self.reload()
        
        return self
    
    def reload(self) -> None:
        self.ui_table.clear()
        
        with self.ui_table:
            self.read()
    
    def setup_cached_dialogs(self) -> None:
        with ui.dialog().props("persistent") as self.ui_loading_dialog:
            ui.spinner(size='xl')
        
        with ui.dialog() as self.ui_autotag_dialog, ui.card():
            ui.markdown(
                "This will autotag all images in the dataset. "
                "This is a slow process, so be patient!\n"
                "This uses `kohya`'s tagger with the `SmilingWolf/wd-v1-4-swinv2-tagger-v2` model.\n"
                "\n"
                "Warning: your tags will be overwritten without any further confirmation!\n"
            )
            
            confidence_slider = labeled_slider(
                "Confidence threshold (higher values give fewer but more accurate tags)",
                value=0.4,
            )
            
            blacklist_tags = ui.textarea(
                "Blacklist tags",
                value=dataset.join_tags([
                    "official alternate costume", "official alternate hairstyle",
                    "official alternate hair length",
                    "alternate costume", "alternate hairstyle",
                    "alternate hair length", "alternate hair color",
                ], trailing_comma=True),
            ).classes("w-full")
            
            with ui.row():
                ui.button("Autotag", on_click=lambda:
                    self.ui_autotag_dialog.submit((
                        confidence_slider.value,
                        dataset.split_tags(blacklist_tags.value),
                    ))
                )
                ui.button("Cancel", on_click=self.ui_autotag_dialog.close)
    
        with ui.dialog() as self.ui_find_duplicates_dialog, ui.card():
            ui.markdown(
                "This will find and select duplicate images in the dataset. "
                "This is a slow process, so be patient!\n"
                "This uses the `imagededup` library.\n"
            )
            
            similarity_slider = labeled_slider(
                "Similarity threshold (how similar two images must be to be considered duplicates)",
                value=0.98,
            )
            
            with ui.row():
                ui.button("Find duplicates", on_click=lambda:
                    self.ui_find_duplicates_dialog.submit((
                        similarity_slider.value,
                    ))
                )
                ui.button("Cancel", on_click=self.ui_find_duplicates_dialog.close)
    
        # TODO: More?
    
    @contextlib.asynccontextmanager
    async def loading_dialog(self) -> typing.Iterator[None]:
        self.ui_loading_dialog.open()
        
        await asyncio.sleep(0)
        
        try:
            yield
        finally:
            self.ui_loading_dialog.close()
    
    def add_controls(self) -> None:
        with ui.column().style('width: 90%'):
            self._add_inputs()
        
            self._add_select_buttons()
        
            self._add_op_buttons()
        
        self._add_selected_badge()

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
        
        self._reset_after_op()
    
    def _reset_after_op(self) -> None:
        if not self.ui_persist_inputs.value:
            self.ui_input_A.value = ""
            self.ui_input_B.value = ""
            self.ui_affect_all.value = False

    def _input_tags(self, field: typing.Literal['A', 'B'] = 'A') -> list[str]:
        assert field in ('A', 'B'), f"Invalid field {field!r}"
        
        return dataset.split_tags(getattr(self, f'ui_input_{field}').value)

    def _add_inputs(self) -> None:
        with ui.row().classes('w-full'):
            # Two common input fields. Should be as wide as possible
            self.ui_input_A = ui.input('A').style('min-width: 600px')  # .style('width: 45%')
            self.ui_input_B = ui.input('B').style('min-width: 600px')  # .style('width: 45%')

    def _add_select_buttons(self) -> None:
        def _find() -> None:
            search: list[str] = self._input_tags('A')
            
            self.for_all(
                lambda item: item.select_set(
                    item.match_tags(search)
                )
            )
            
            self._reset_after_op()
        
        def _find_in_selection() -> None:
            search: list[str] = self._input_tags('A')
            base_all: bool = self.ui_affect_all.value
            
            self.for_all(
                lambda item: item.select_set(
                    (base_all or item.selected)
                    and item.match_tags(search)
                )
            )
            
            self._reset_after_op()
        
        with ui.row():
            ui.button("Select all", on_click=self.select_all)
            ui.button("Reset selection", on_click=self.select_none)
            ui.button("Invert selection", on_click=self.select_invert)
            
            ui.button("Find A", on_click=_find)
            ui.button("Find A in selection", on_click=_find_in_selection)
            
            self.ui_affect_all = ui.checkbox("Affect everything")
            self.ui_persist_inputs = ui.checkbox("Persist inputs")

    def _add_selected_badge(self) -> None:
        with (
            ui.page_sticky('top-right', x_offset=20, y_offset=20).style('z-index: 1000'),
            ui.card(),
        ):
            ui.markdown() \
                .classes("no-bootom-margin") \
                .bind_content_from(self, 'selected_cnt', lambda x: f"Selected: **{x}**")

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
            on_click=self._ask_autotag,
            color='purple',
        )
        ui.button(
            "Find duplicates",
            on_click=self._ask_find_duplicates,
            color='purple',
        )
        
        ui.button(
            "Remove images",
            on_click=self._ask_remove_images,
            color='red',
        )
    
    async def _ask_autotag(self) -> None:
        result: tuple[float, list[str]] | None = await self.ui_autotag_dialog
        
        if result is None:
            return
        
        async with self.loading_dialog():
            await self.autotag(*result)
    
    async def autotag(self, threshold: float, blacklist_tags: list[str]) -> None:
        for file in self.path.glob(f"*{self.tags_file_ext}"):
            file.unlink()
        
        await run_kohya_async(
            "finetune/tag_images_by_wd14_tagger.py",
            kohya_path=KOHYA_PATH,
            args=[
                f"{self.path}",
                "--repo_id=SmilingWolf/wd-v1-4-swinv2-tagger-v2",
                "--model_dir=./cache",
                f"--thresh={threshold}",
                "--batch_size=8",
                f"--caption_extension={self.tags_file_ext}",
            ],
            env=dict(
                TF_CPP_MIN_LOG_LEVEL="2",
            ),
        )
        
        self.reload()
        
        for item in self.items:
            item.set_tags(remove_tags_underscores(item.tags))
            item.remove_tags(blacklist_tags)
        
        self.flush()
        
        ui.notify("Autotagging complete!", type='success')
    
    async def _ask_find_duplicates(self) -> None:
        result: tuple[float] | None = await self.ui_find_duplicates_dialog
        
        if result is None:
            return
        
        async with self.loading_dialog():
            await self.find_duplicates(*result)
    
    async def find_duplicates(self, threshold: float) -> None:
        ui.notify('Not implemented yet!', type='info')
    
    async def _ask_remove_images(self) -> None:
        with ui.dialog() as dialog, ui.card():
            which: str = "the selected"
            assert self.selected_cnt == len(self.get_selection()), "Sanity check failed!"
            count: int = self.selected_cnt
            
            if self.ui_affect_all.value:
                which = "ALL"
                count = len(self)
            
            ui.markdown(
                f"Are you sure you want to delete {which} images ({count}) from this dataset?\n\n"
                f" - Selecting 'Yes' will mark the images and tags with `.deleted` suffix.\n"
                f" - Selecting 'DELETE PERMANENTLY' will permanently delete the image and tag files. Use with caution!\n"
            )
            
            def apply(soft: bool) -> None:
                dialog.submit((
                    'all' if self.ui_affect_all.value else 'selected',
                    soft,
                ))
            
            with ui.row().classes('w-full'):
                ui.button("Yes", on_click=lambda: apply(soft=True), color='amber')
                ui.button("No", on_click=dialog.close)
                
                safety = ui.switch().style('margin-left: auto')
                delete_hard = ui.button("DELETE PERMANENTLY", on_click=lambda: apply(soft=False), color='red')
                
                delete_hard.disable()
                safety.bind_value(delete_hard, 'enabled')
        
        result: tuple[str, bool] | None = await dialog
        
        if result is None:
            return

        async with self.loading_dialog():
            self.remove_images(*result)
    
    # TODO: Make async somehow?
    def remove_images(self, mode: typing.Literal['selected', 'all'], soft: bool = True) -> None:
        super().remove_images(mode, soft)
        
        self.reload()


def run_ui(
    *,
    kohya_path: str | pathlib.Path,
    port: int | None = None,
    dataset_path: str | pathlib.Path | None = None,
    show: bool = False,
    dark_mode: bool = False,
) -> None:
    if isinstance(kohya_path, str):
        kohya_path = pathlib.Path(kohya_path)
    
    assert kohya_path.is_dir(), f"Invalid kohya path: {kohya_path}"
    
    global KOHYA_PATH
    KOHYA_PATH = kohya_path
    
    ui.add_head_html(GLOBAL_CSS)
    
    ui.switch("Toggle dark mode", on_change=toggle_dark).set_value(dark_mode)
    
    with ui.row():
        dataset_path_field = ui.input("Dataset path", placeholder="C:\\my_datasets\\dataset1").style("min-width: 600px")
        # TODO: Allow picking the tag file extension as well?
        dataset_pick_btn = ui.button("📁").props("size=lg")
        dataset_load_btn = ui.button("Load dataset").props("size=lg")
        dataset_save_btn = ui.button("Save to disk", color='orange').props("size=lg")
    
        async def pick_dataset() -> None:
            start: str = dataset_path_field.value
            
            if not start.strip():
                start = "/"
            
            folder = await local_file_picker(
                start,
                upper_limit=None,
                expect_dir=True,
            )
            
            if folder is None:
                return
            
            dataset_path_field.value = str(folder)
        
        dataset_pick_btn.on(
            "click",
            lambda _: pick_dataset(),
        )

    dataset_controls = ui.row().classes('w-full justify-between')
    table = ui.row().classes('w-full')
    
    def _load_dataset() -> None:
        ds: UIDataset = UIDataset.from_path(dataset_path_field.value)
        
        ds.setup(dataset_controls, table)
        
        dataset_save_btn.on(
            "click",
            lambda _: ds.flush(),
        )
    
    dataset_load_btn.on(
        "click",
        lambda _: _load_dataset(),
    )

    with ui.page_sticky('bottom-right', x_offset=20, y_offset=20).style('z-index: 1000'):
        ui.button("Scroll to the top", on_click=scroll_top)
    
    if dataset_path:
        dataset_path_field.value = str(dataset_path)
        _load_dataset()
    
    ui.run(
        title="Dataset Tag Editor",
        port=port or 8080,
        reload=False,
        show=show,
    )


__all__ = [
    "run_ui",
]
