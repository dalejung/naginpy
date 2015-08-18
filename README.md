# naginpy

Build out tooling to create localized DSLs.

Currently this is all prototype phase and feels like multiple pythons eating the tails of other pythons.

[Original blabbings on this stuff](https://github.com/dalejung/edamame)

I need to collate notes and organize. naginpy, quantreactor, edamame, etc are kind of parts of a larger thing.

[free flow notes](https://github.com/dalejung/naginpy/blob/master/NOTES.md)

# Plan

**Interactive/Import Engine**

Create DSL engines that will work both in `IPython` and python proper via transformers and import hooks respectively. This will require modules execute their code line-by-line to mimic the `IPython` flow.

One of the main caveats here is that the engine must be involved determining when logical lines end. This is require to allow things like `dplr`s `%>%` operator to work interactively.

**SyntaxError Nodes**

During AST creation, syntax errors that are self contained should not result in a `SyntaxError`, but instead create a node that contains the errant text.

Example of syntax erros that we would want to keep around for engines.


```python
# function params
bob = lm(y ~ x1 + x2 + x3, data=mydata) # ~ is not a binaryop

# block level
with dplr():
      mtcars %>%
      subset(hp > 100) %>%
      aggregate(. ~ cyl, data = ., FUN = . %>% mean %>% round(2)) %>%
      transform(kpl = mpg %>% multiply_by(0.4251)) %>%
      print
```

The first example would be useful for the non-standard eval engine. The second example would allow one to create mini-dsls that existed only within a scope. Kind of like an `IPython` `magics` but compatible outside of interactive.

## Special Eval

The Special Eval harnass can be thought of as the following process.

**AST Generation**

Run textual preprocessing and then create an AST. The tree might include marker nodes that represent syntax errors.

**Upward Engine Traversal**

From each leaf node (`Name(ctx=Load())`) allow engines to walk up the tree. This is done by depth.

In the line: `pd.rolling_sum(df.iloc[df.a > 5], 5)`

`pd` and `df` would be the leaf nodes. They also represent our current `ExecutionContext`.

Each engine is allowed to modify the tree and access the object represented by the current node. Right now, that is restricted to `Name` and `Attribute`.

Note: kernel object access is lazy and we keep a tab on what was accessed. We replace the `Attribute` node with the evaled attribute. This is because attribute access may have side effects in python and we guarantee only single access.

The reason we even allow Engines to access the Node's object is to trigger behavior based on the object value and not just `AST`. Example of this would be the `nse` decorator to signal that a python function wants its argument passed in as strings ala `R`.

Another example is marking `DataFrame` methods as being `inplace` and doing special handling.

**Final exec**

After all the engines have done their AST monkeying and partial evaluations, we run through and make sure no `SyntaxError` marker nodes exist and check that all previously accessed `Attribute` nodes are replaced with the value.

The object access and piecemeal evaluation is what gives the engine more power over simple textual/ast transforms.

### Computable / Manifests

In special eval, each expression is represented as a `Manifest` which includes the `Expression` and `ExecutionContext`. A Manifest is by definition deferred, as it just represents the information needed to create a value. A `Computable` represents the possible execution of a `Manifest`. It stores the value and extra info like computation time.

**`Expression`**

Currently we only handle ASTs. This might always be the case but the only real requirement is that an `Expression` is stateless and compute a value with an `ExecutionContext`

**`ExecutionContext`**

A dict like structure that represents the variables needed to recreate the same value when plugged in with an `Expression`. Note that an `ExecutionContext` can be stateful, in that it refers to object in kernel and would not surive a restart. All values are currently either `Manifest` or `ContextObjects`. Whether it is stateless depends on whether all of its values are stateless. Examples of stateless values would be something like a csv filename with a timestamp. 

**Stateless**

So an important concept is whether a `Manifest` is stateless which depends on its context. A stateless `Manifest` should give you the same value with kernel restart or even another machine, given that the machine understands the `ContextObject`'s key and how to grab the same data.


## Example Engines

### NSE - Non Standard Eval

This one is fairly simple. We allow functions to be wrapped with a `@nse` decorator to dictate that parameters need not be:

1. valid python syntax
2. references to existing variables

The idea is to act like `R`'s NSE but with an explicit decorator.'


### DataCache

Manifests can be stateless and nested. This allows us to:

**prevent recomputation**

Prevent recomputation of data that already exists.

**external persistance**

Due to Special Eval handling all execution, we have access to timing metrics that can determine whether to persist the data to some cache backend. We can base this on exec timing, datashape, speed of cache, etc. We can even prune memory based caching. Maybe an intermediate expression isn't worth keeping in memory since it can be recomputed from a source frame that is in memory.

**break up expressions**

Because a stateless manifest can be broken up into multiple stateless manifest, we can take a complex line like:

```python
pd.rolling_sum(df.iloc[df.a > 5], 5) + some_slow_func(df)
```

and break it up into 

```python
A = df.a > 5
B = df.iloc[A]
C = pd.rolling_sum(B), 5)
D = some_slow_func(df)
E = C + D
```

Each one can be evaled and measured on its own performance characteristics. It we have memory, maybe we keep `D` around because we use it on multiple lines.

### DeferEngine

The previous `DataCache` engine is meant to be dropin. While Special Eval deals in deferred `Manifest`, `DataCache` would just eval them immediately to maintain backwards compat. However, it's possible to just defer completely. A simple plan would be just to return a manifest and then execute the manifest later on. The engine will create the proper nested `Manifest`. 

However, because Special Eval allows access to the object associated with a Node, we can create specialized Deferred objects like a `DeferredFrame` that replicates `pandas.DataFrame` but do things like defer operations so they can be run through `numexpr`. Conceptually, one could translate regular `pandas` into `blaze` representations. Or make it like a virtual frame for out of core work. Though the virtual frame may not necessarily require special eval.


## why?

Kind of weird to have this last. 

1. Replicate the real good parts of `R`.
2. DataCaching
3. Being able to have Manifests on everything. Tying Manifests to things like images/reports.
4. Being able to publish a single notebook cell at the bottom of the page, and have it offload to some external servers and be fully interactive. The external servers could get the exact data. Have the ability to change paramters that created the output like resample periods.

blah blah blah
