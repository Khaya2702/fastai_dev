#AUTOGENERATED! DO NOT EDIT! File to edit: dev/10_data_block.ipynb (unless otherwise specified).

__all__ = ['DataBlock']

@docs
class DataBlock():
    "Generic container to quickly build `DataSource` and `DataBunch`"
    default_dl_tfms = Cuda
    def __init__(self, types=None, get_items=None, splitter=None, labeller=None):
        if types is not None:     self.types = types
        if get_items is not None: self.get_items = get_items
        if splitter is not None:  self.splitter = splitter
        if labeller is not None:  self.labeller = labeller

    def get_items(self, source): pass
    def splitter(self, items): pass
    def labeller(self, item): pass

    def datasource(self, source, type_tfms=None, ds_tfms=None):
        items = self.get_items(source)
        splits = self.splitter(items)
        if type_tfms is None: type_tfms = [L() for t in self.types]
        type_tfms = L(mix_tfms(getattr(t, 'default_type_tfms', L()), tfm) for (t,tfm) in zip(self.types, type_tfms))
        type_tfms = type_tfms[0] + L(self.labeller + L(tfm) for tfm in type_tfms[1:])
        ds_tfms = L(mix_tfms(*[getattr(t, 'default_ds_tfms', L()) for t in self.types], ds_tfms))
        return DataSource(items, type_tfms=type_tfms, ds_tfms=ds_tfms, filts=splits)

    def databunch(self, source, type_tfms=None, ds_tfms=None, dl_tfms=None, bs=16, **kwargs):
        dsrc = self.datasource(source, type_tfms=type_tfms, ds_tfms=ds_tfms)
        dl_tfms = L(mix_tfms(*[getattr(t, 'default_dl_tfms', L()) for t in self+L(self.types)], dl_tfms))
        return dsrc.databunch(tfms=dl_tfms, bs=bs, **kwargs)

    _docs = dict(get_items="Pass at init or implement how to get your raw items from a `source`",
                 splitter="Pass at init or implement how to split your `items`",
                 labeller="Pass at init or implement how to label a raw `item`",
                 datasource="Create a `Datasource` from `source` with `tfms` and `tuple_tfms`",
                 databunch="Create a `DataBunch` from `source` with `tfms`")