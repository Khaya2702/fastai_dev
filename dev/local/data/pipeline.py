#AUTOGENERATED! DO NOT EDIT! File to edit: dev/02_data_pipeline.ipynb (unless otherwise specified).

__all__ = ['get_func', 'show_title', 'Func', 'Sig', 'SelfFunc', 'Self', 'positional_annotations', 'Transform',
           'compose_tfms', 'Pipeline', 'TfmdList', 'TfmdDS']

from ..imports import *
from ..test import *
from ..core import *
from ..notebook.showdoc import show_doc

def get_func(t, name, *args, **kwargs):
    "Get the `t.name` (potentially partial-ized with `args` and `kwargs`) or `noop` if not defined"
    f = getattr(t, name, noop)
    return f if not (args or kwargs) else partial(f, *args, **kwargs)

def show_title(o, ax=None, ctx=None):
    "Set title of `ax` to `o`, or print `o` if `ax` is `None`"
    ax = ifnone(ax,ctx)
    if ax is None: print(o)
    else: ax.set_title(o)

class Func():
    "Basic wrapper around a `name` with `args` and `kwargs` to call on a given type"
    def __init__(self, name, *args, **kwargs): self.name,self.args,self.kwargs = name,args,kwargs
    def __repr__(self): return f'sig: {self.name}({self.args}, {self.kwargs})'
    def _get(self, t): return get_func(t, self.name, *self.args, **self.kwargs)
    def __call__(self,t): return L(t).mapped(self._get) if is_listy(t) else self._get(t)

class _Sig():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return Func(k, *args, **kwargs)
        return _inner

Sig = _Sig()

class SelfFunc():
    "Search for `name` attribute and call it with `args` and `kwargs` on any object it's passed."
    def __init__(self, nm, *args, **kwargs): self.nm,self.args,self.kwargs = nm,args,kwargs
    def __repr__(self): return f'self: {self.nm}({self.args}, {self.kwargs})'
    def __call__(self, o):
        if not is_listy(o): return getattr(o,self.nm)(*self.args, **self.kwargs)
        else: return [getattr(o_,self.nm)(*self.args, **self.kwargs) for o_ in o]

class _SelfFunc():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return SelfFunc(k, *args, **kwargs)
        return _inner

Self = _SelfFunc()

def positional_annotations(f):
    "Get list of annotated types for all positional params, or None if no annotation"
    sig = inspect.signature(f)
    return [p.annotation if p.annotation != inspect._empty else None
            for p in sig.parameters.values() if p.default == inspect._empty and p.kind != inspect._VAR_KEYWORD]

from multimethod import multimeta,DispatchError

class Transform(metaclass=multimeta):
    "A function that `encodes` if `filt` matches, and optionally `decodes`"
    order,add_before_setup,filt,t = 0,False,None,None
    def __init__(self,encodes=None,decodes=None):
        self.encodes = getattr(self, 'encodes', noop) if encodes is None else encodes
        self.decodes = getattr(self, 'decodes', noop) if decodes is None else decodes

    def _apply(self, fs, x, filt):
        if self.filt is not None and self.filt!=filt: return x
        if self.t:
            gs = self._get_func(fs, self.t)
            if is_listy(self.t) and len(positional_annotations(gs)) != len(self.t):
                gs = [self._get_func(fs,t_) for t_ in self.t]
                if len(gs) == 1: gs = gs[0]
        else: gs=fs
        if is_listy(gs): return tuple(f(x_) for f,x_ in zip(gs,x))
        return gs(*L(x))

    def _get_func(self,f,t):
        if not hasattr(f,'__func__'): return f
        idx = (object,) + tuple(t) if is_listy(t) else (object,t)
        try: f = f.__func__[idx]
        except DispatchError: return noop
        return partial(f,self)

    def accept_types(self, t): self.t = t
        # We can't create encodes/decodes here since patching might change things later
        # So we call _get_func in _apply instead

    def __call__(self, x, filt=None): return self._apply(self.encodes, x, filt)
    def decode  (self, x, filt=None): return self._apply(self.decodes, x, filt)
    def __getitem__(self, x): return self(x) # So it can be used as a `Dataset`

add_docs(Transform,
         __call__="Dispatch and apply the proper encodes to `x` if `filt` matches",
         decode="Dispatch and apply the proper decodes to `x` if `filt` matches",
         accept_types="Indicate the type of input received by the transform is `t`")

def compose_tfms(x, tfms, func_nm='__call__', reverse=False, **kwargs):
    "Apply all `func_nm` attribute of `tfms` on `x`, maybe in `reverse` order"
    if reverse: tfms = reversed(tfms)
    for tfm in tfms: x = getattr(tfm,func_nm,noop)(x, **kwargs)
    return x

def _get_ret(func):
    "Get the return annotation of `func`"
    ann = getattr(func,'__annotations__', None)
    if not ann: return None
    typ = ann.get('return')
    return list(typ.__args__) if getattr(typ, '_name', '')=='Tuple' else typ

class Pipeline():
    "A pipeline of composed (for encode/decode) transforms, setup with types"
    def __init__(self, funcs=None, t=None):
        if isinstance(funcs, Pipeline): funcs = funcs.raws
        self.raws,self.fs,self.t_show = L(funcs),[],None
        if len(self.raws) == 0: self.final_t = t
        else:
            for i,f in enumerate(self.raws.sorted(key='order')):
                if not isinstance(f,Transform): f = Transform(f)
                f.accept_types(t)
                self.fs.append(f)
                if self.t_show is None and hasattr(t, 'show'): self.t_idx,self.t_show = i,t
                t = _get_ret(f.encodes) or t
            if self.t_show is None and hasattr(t, 'show'): self.t_idx,self.t_show = i+1,t
            self.final_t = t

    def new(self, t=None): return Pipeline(self, t)
    def __repr__(self): return f"Pipeline over {self.fs}"

    def setup(self, items=None):
        tfms,raws,self.fs,self.raws = self.fs,self.raws,[],[]
        for t,r in zip(tfms,raws.sorted(key='order')):
            if t.add_before_setup:     self.fs.append(t) ; self.raws.append(r)
            if hasattr(t, 'setup'):    t.setup(items)
            if not t.add_before_setup: self.fs.append(t) ; self.raws.append(r)

    def __call__(self, o, filt=None): return compose_tfms(o, self.fs, filt=filt)
    def decode  (self, i, filt=None): return compose_tfms(i, self.fs, func_nm='decode', reverse=True, filt=filt)
    #def __getitem__(self, x): return self(x)
    #def decode_at(self, idx): return self.decode(self[idx])
    #def show_at(self, idx):   return self.show(self[idx])

    def show(self, o, ctx=None, filt=None, **kwargs):
        if self.t_show is None: return self.decode(o, filt=filt)
        o = compose_tfms(o, self.fs[self.t_idx:], func_nm='decode', reverse=True, filt=filt)
        return self.t_show.show(o, ctx=ctx, **kwargs)

add_docs(Pipeline,
         __call__="Compose `__call__` of all `tfms` on `o`",
         decode="Compose `decode` of all `tfms` on `i`",
         new="Create a new `Pipeline`with the same `tfms` and a new initial `t`",
         show="Show item `o`",
         setup="Go through the transforms in order and call their potential setup on `items`")

@docs
class TfmdList(GetAttr):
    "A `Pipeline` of `tfms` applied to a collection of `items`"
    _xtra = 'decode __call__ show'.split()

    def __init__(self, items, tfms, do_setup=True):
        self.items = L(items)
        self.default = self.tfms = Pipeline(tfms)
        if do_setup: self.setup()

    def __getitem__(self, i, filt=None):
        "Transformed item(s) at `i`"
        its = self.items[i]
        return its.mapped(self.tfms, filt=filt) if is_iter(i) else self.tfms(its, filt=filt)

    def setup(self): self.tfms.setup(self)
    def subset(self, idxs): return self.__class__(self.items[idxs], self.tfms, do_setup=False)
    def decode_at(self, idx, **kwargs): return self.decode(self[idx], **kwargs)
    def show_at(self, idx, **kwargs): return self.show(self[idx], **kwargs)
    def __eq__(self, b): return all_equal(self, b)
    def __len__(self): return len(self.items)
    def __iter__(self): return (self[i] for i in range_of(self))
    def __repr__(self): return f"{self.__class__.__name__}: {self.items}\ntfms - {self.tfms}"

    _docs = dict(setup="Transform setup with self",
                 decode_at="Decoded item at `idx`",
                 show_at="Show item at `idx`",
                 subset="New `TfmdList` that only includes items at `idxs`")

class TfmdDS(TfmdList):
    def __init__(self, items, tfms=None, tuple_tfms=None, do_setup=True):
        if tfms is None: tfms = [None]
        self.items,self.tfms = items,tfms
        self.tfmd_its = [TfmdList(items, t, do_setup=do_setup) for t in tfms]
        self.tuple_tfms = Pipeline(tuple_tfms, t=[it.tfms.final_t for it in self.tfmd_its])
        if do_setup: self.setup()

    def __getitem__(self, i, filt=None):  #TODO add filt
        its = _maybe_flat([it.__getitem__(i, filt=filt) for it in self.tfmd_its])
        if is_iter(i):
            if len(self.tfmd_its) > 1: its = zip(*L(its))
            return L(its).mapped(self.tuple_tfms, filt=filt)
        return self.tuple_tfms(its, filt=filt)

    def decode(self, o, filt=None):
        o = self.tuple_tfms.decode(o, filt=filt)
        return _maybe_flat([it.decode(o_, filt=filt) for o_,it in zip(o,self.tfmd_its)])

    def show(self, o, ctx=None, filt=None, **kwargs):
        if self.tuple_tfms.t_show is not None: return self.tuple_tfms.show(o, ctx=ctx, **kwargs)
        o = self.tuple_tfms.decode(o, filt=filt)
        for o_,it in zip(o,self.tfmd_its): ctx = it.show(o_, ctx=ctx, **kwargs)
        return ctx

    def decode_batch(self, b, filt=None):
        transp = L(zip(*L(b)))
        return transp.mapped(self.decode, filt=filt).zipped()

    def setup(self): self.tuple_tfms.setup(self)

    def subset(self, idxs):
        return self.__class__(self.items[idxs], self.tfms, self.tuple_tfms, do_setup=False)

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.items}\ntfms - {self.tfms}\ntuple tfms - {self.tuple_tfms}"

add_docs(TfmdDS,
         "A `Dataset` created from raw `items` by calling each element of `tfms` on them",
         __getitem__="Call all `tfms` on `items[i]` then all `tuple_tfms` on the result",
         decode="Compose `decode` of all `tuple_tfms` then all `tfms` on `i`",
         show="Show item `o` in `ctx`",
         decode_batch="Call `self.decode` on all elements of `b`",
         setup="Go through the transforms in order and call their potential setup on `items`",
         subset="New `TfmdDS` that only includes items at `idxs`")