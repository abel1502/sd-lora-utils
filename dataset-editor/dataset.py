from __future__ import annotations
import typing
import pathlib
from dataclasses import dataclass, field
import warnings


def split_tags(text: str) -> list[str]:
    return [x for x in map(str.strip, text.split(',')) if x]


def join_tags(tags: list[str], *, trailing_comma: bool = False) -> str:
    return ', '.join(tags) + (',' if trailing_comma and tags else '')


@dataclass
class DatasetItem:
    parent: Dataset
    img_file: pathlib.Path
    tags_file: pathlib.Path
    tags: list[str] = field(default_factory=list)
    selected: bool = False
    dirty: bool = False
    deleted: bool = False
    
    def __post_init__(self) -> None:
        self.reload()
    
    def flush(self, force: bool = False) -> None:
        if self.dirty or force:
            self.tags_file.write_text(join_tags(self.tags))
        
        self.on_reset()
    
    def reload(self) -> None:
        if self.tags_file.exists():
            self.tags = split_tags(self.tags_file.read_text())
        else:
            self.tags_file.touch()
            self.tags = []
        
        self.on_reset()
    
    def delete(self, soft: bool = True) -> None:
        self.deleted = True
        
        if soft:
            self.img_file.rename(self.img_file.with_suffix(self.img_file.suffix + ".deleted"))
            self.tags_file.rename(self.tags_file.with_suffix(self.tags_file.suffix + ".deleted"))
        else:
            warnings.warn("Permanently deleting an image!")
            self.img_file.unlink(missing_ok=True)
            self.tags_file.unlink(missing_ok=True)
    
    def select_invert(self) -> None:
        self.on_selected(not self.selected)
    
    def select_set(self, value: bool = True) -> None:
        self.on_selected(value)
    
    def on_changed(self) -> None:
        self.dirty = True
    
    def on_reset(self) -> None:
        self.dirty = False
    
    def on_selected(self, state: bool) -> None:
        self.selected = state
    
    def deduplicate(self) -> None:
        old_len: int = len(self.tags)
        
        # To maintain order
        self.tags = list(dict.fromkeys(
            filter(None, map(str.strip, self.tags))
        ))
        
        if len(self.tags) != old_len:
            self.on_changed()
    
    def set_tags(self, tags: str | typing.Collection[str]) -> None:
        if isinstance(tags, str):
            tags = [tags]
        
        self.tags = list(tags)
        self.deduplicate()
        self.on_changed()  # TODO: only if changed?
    
    def prepend_tags(self, tags: str | typing.Collection[str]) -> None:
        old_len: int = len(self.tags)
        
        if isinstance(tags, str):
            tags = [tags]
        
        self.tags = list(tags) + self.tags
        self.deduplicate()
        
        if len(self.tags) != old_len:
            self.on_changed()
    
    def add_tags(self, tags: str | typing.Collection[str]) -> None:
        old_len: int = len(self.tags)
        
        if isinstance(tags, str):
            tags = [tags]
        
        self.tags += list(tags)
        self.deduplicate()
        
        if len(self.tags) != old_len:
            self.on_changed()
    
    def remove_tags(self, tags: str | typing.Collection[str]) -> None:
        old_len: int = len(self.tags)
        
        if isinstance(tags, str):
            tags = [tags]
        tags = set(tags)
        
        self.tags = [i for i in self.tags if i not in tags]
        
        if len(self.tags) != old_len:
            self.on_changed()
    
    def match_tags(
        self,
        tags: str | typing.Collection[str],
    ) -> bool:
        if isinstance(tags, str):
            tags = [tags]
        
        return all(i in self.tags for i in tags)
    
    def replace_tags(
        self,
        search: str | typing.Collection[str],
        replace: str | typing.Collection[str],
    ) -> None:
        if not self.match_tags(search):
            return
        
        self.remove_tags(search)
        self.add_tags(replace)
    
    def convert_to_png(self) -> None:
        raise NotImplementedError()  # TODO


def multi_ext_glob(path: pathlib.Path, exts: typing.Collection[str]) -> typing.Iterable[pathlib.Path]:
    for ext in exts:
        assert ext.startswith('.'), f"Extension '{ext}' must start with a dot"
        yield from path.glob(f"**/*{ext}")


@dataclass
class Dataset:
    ITEM_CLS: typing.ClassVar[typing.Type[DatasetItem]] = DatasetItem
    
    path: pathlib.Path
    items: list[DatasetItem] = field(default_factory=list)
    tags_file_ext: str = ".txt"

    def read(self) -> None:
        self.items = []
        
        existing_tags_files: int = 0
        
        for img_path in multi_ext_glob(self.path, ['.jpg', '.jpeg', '.png']):
            tags_path: pathlib.Path = img_path.with_suffix(self.tags_file_ext)
            existing_tags_files += tags_path.exists()
            
            self.items.append(self.ITEM_CLS(self, img_path, tags_path))
        
        if existing_tags_files < len(self.items):
            warnings.warn(
                f"In dataset found {len(self.items)} image files, but {existing_tags_files or 'no'} caption files."
            )

    @property
    def unsaved_changes_cnt(self) -> int:
        return sum(item.dirty for item in self.items)
    
    def for_all(self, func: str | typing.Callable[[DatasetItem], typing.Any], *args, **kwargs) -> None:
        if isinstance(func, str):
            func = getattr(self.ITEM_CLS, func)
        
        for item in self.items:
            func(item, *args, **kwargs)
    
    def for_selected(self, func: str | typing.Callable[[DatasetItem], typing.Any], *args, **kwargs) -> None:
        if isinstance(func, str):
            func = getattr(self.ITEM_CLS, func)
        
        for item in self.items:
            if item.selected:
                func(item, *args, **kwargs)
    
    def select_all(self) -> None:
        for item in self.items:
            item.select_set(True)
    
    def select_none(self) -> None:
        for item in self.items:
            item.select_set(False)
    
    def select_invert(self) -> None:
        for item in self.items:
            item.select_invert()
    
    def flush(self) -> None:
        for item in self.items:
            item.flush()
    
    def remove_images(self, mode: typing.Literal['selected', 'all'], soft: bool = True) -> None:
        assert mode in ('selected', 'all'), f"Invalid mode {mode!r}"
        
        getattr(self, f"for_{mode}")(self.ITEM_CLS.delete, soft=soft)
        
        self.items = [item for item in self.items if not item.deleted]
    
    def __len__(self) -> int:
        return len(self.items)
    
    def get_selection(self) -> list[DatasetItem]:
        return [item for item in self.items if item.selected]


__all__ = [
    "split_tags",
    "join_tags",
    "DatasetItem",
    "Dataset",
]
