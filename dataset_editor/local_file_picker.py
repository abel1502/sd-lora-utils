# Credit: https://github.com/zauberzeug/nicegui/blob/main/examples/local_file_picker/local_file_picker.py

from __future__ import annotations
import typing
import platform
import pathlib
from typing import Any

from nicegui import ui


class local_file_picker(ui.dialog):
    path: pathlib.Path
    upper_limit: pathlib.Path | None
    show_hidden_files: bool
    grid: ui.aggrid
    multiple: bool
    expect_dir: bool = False
    
    def __init__(
        self,
        directory: str,
        *,
        upper_limit: str | None = ...,
        multiple: bool = False,
        show_hidden_files: bool = False,
        expect_dir: bool = False,
    ) -> None:
        """
        Local File Picker

        This is a simple file picker that allows you to select a file from the local filesystem where NiceGUI is running.

        :param directory: The directory to start in.
        :param upper_limit: The directory to stop at (None: no limit, default: same as the starting directory).
        :param multiple: Whether to allow multiple files to be selected.
        :param show_hidden_files: Whether to show hidden files.
        """
        
        super().__init__()

        self.path = pathlib.Path(directory).expanduser()
        if upper_limit is None:
            self.upper_limit = None
        else:
            self.upper_limit = pathlib.Path(directory if upper_limit == ... else upper_limit).expanduser()
        self.show_hidden_files = show_hidden_files
        self.multiple = multiple
        self.expect_dir = expect_dir

        with self, ui.card():
            self.add_drives_toggle()
            self.grid = ui.aggrid({
                'columnDefs': [{'field': 'name', 'headerName': 'File'}],
                'rowSelection': 'multiple' if multiple else 'single',
            }, html_columns=[0]).classes('w-96').on('cellDoubleClicked', self.handle_double_click)
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=self.close).props('outline')
                ui.button('Ok', on_click=self._handle_ok)
        self.update_grid()

    def add_drives_toggle(self) -> None:
        if platform.system() == 'Windows':
            import win32api
            drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            
            active_drive: str = drives[0]
            
            if self.path.drive + "\\" in drives:
                active_drive = self.path.drive + "\\"
            
            self.drives_toggle = ui.toggle(drives, value=active_drive, on_change=self.update_drive)

    def update_drive(self) -> None:
        self.path = pathlib.Path(self.drives_toggle.value).expanduser()
        self.update_grid()

    def update_grid(self) -> None:
        paths = list(self.path.glob('*'))
        if not self.show_hidden_files:
            paths = [p for p in paths if not p.name.startswith('.')]
        if self.expect_dir:
            paths = [p for p in paths if p.is_dir()]
        paths.sort(key=lambda p: p.name.lower())
        paths.sort(key=lambda p: not p.is_dir())

        self.grid.options['rowData'] = [
            {
                'name': f'📁 <strong>{p.name}</strong>' if p.is_dir() else p.name,
                'path': str(p),
            }
            for p in paths
        ]
        if self.upper_limit is None and self.path != self.path.parent or \
                self.upper_limit is not None and self.path != self.upper_limit:
            self.grid.options['rowData'].insert(0, {
                'name': '📁 <strong>..</strong>',
                'path': str(self.path.parent),
            })
        self.grid.update()

    def handle_double_click(self, msg: dict[str, typing.Any]) -> None:
        self.path = pathlib.Path(msg['args']['data']['path'])
        if self.path.is_dir():
            self.update_grid()
        else:
            self.submit([self.path])

    async def _handle_ok(self) -> None:
        rows = [
            pathlib.Path(r['path'])
            for r in
            await ui.run_javascript(f'getElement({self.grid.id}).gridOptions.api.getSelectedRows()')
        ]
        
        if self.expect_dir and not rows:
            rows = [self.path]
        
        self.submit(rows)
    
    def submit(self, result: pathlib.Path | list[pathlib.Path]) -> None:
        if isinstance(result, pathlib.Path):
            result = [result]
        
        assert isinstance(result, list), "result must be a list of paths"
        
        if not self.multiple:
            assert len(result) == 1
            result = result[0]
        
        return super().submit(result)

__all__ = [
    "local_file_picker",
]
