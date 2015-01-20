# 01-17-15

Multiple physical keys that really point to the same thing.

```python
df.tail(10) {df : df}
pd.DataFrame.tail(df, 10) { pd:pd, df:df }
DataFrame.tail(df, 10) { DataFrame: pd.DataFrame }
tail(10) { tail: df.tail, df: df, df: pd.DataFrame}
```

```
df.tail(10) {df : df}
```
Technically `df.tail` could have been a monkey patched method that overrode. So in order to get the true logical key here, we can't just say that we have:

1. `df` is a pd.DataFrame
2. tail is an attribute
3. tail exists on pd.DataFrame
4. **tail is pd.DataFrame.tail**

This definitely is not always going to be true. 

```
tail = df.tail
tail(10) { tail: df.tail, df: df, df: pd.DataFrame}
```

Note that `tail` would have had it's own manifest. It should not require that though to come from the same key.

Also, we need more state here because `tail` could conceivably depend on some state somewhere. 

## Manifest Types:

### Physical Manifest

Basically based on the actual `ast`. Multiple manifests can actually represent the same logical and semantic versions.

### Logical Manfiest

This a manifest that is stable regardless of source text difference. As long as the actual objects/libs are the same.

```python
df.tail(10) {df : df}
pd.DataFrame.tail(df, 10) { pd:pd, df:df }
```

Should have the same Logical Manifest.

### Semantic Manfiest

Technically a semantic manifest might really only apply to stateless Context objects.

What is kind of fun is that Context and Manifest are kind of the same thing.
Essentially the semantic manfiest is something like, ``("AAPL", "2001-01-01",
"2010-01-01", '1m', 'v!sdfFJDKmnd')``

## open questions

How much context needs to be included for the physical/logical manifests. If we
expand out  `tail(10)` include the fact that it is a member method of
`pd.DataFrame`, however the `tail` output might be different between different
versions of `pandas`. So we would need to include the `pandas` version. 

So you can see that a single variable require a manifest the works up something
of a context tree. 

```
tail
  DataFrame
    pd
```

So the general of a stateless/semantic identifier is that we can just
short-circuit, if these two objects have the same identifier then we just assume
they are the same.

## Computation managers

So everything, including functions defined locally can have a key. Two
environments that are identical need less information than a barebones system.
So we would need to log and keep everything around. If you have a python
function, and then you change it and run it through our reactor, we would
automatically version it in some sense and keep all copies around.

When I'm sending a dataset or something to another environment, they can sync up
differently dpending on the environments. I might have a custom module that is
locally installed, at that point we can pickle the function used or something
like have the remote evnironment install the module

But really the whole point of this is that everything goes through our eval
system, therefore we can log every manifest. It's 2014, we can log every
function ever defined.

# 01-19-15

## manifest equivalence

Been playing with how to equivalize expression that are semantically the same, but not literally equivalent.

### localized method types

In reality, the Manifest of 

```python
"tail" { "tail": df.tail }
```

is not the same as 

```python
"df.tail" { "df": df }
```

The second form involves an attribute access to get `tail` where as the first one has already gotten tail and cached it locally. Imagine the following class:

```python
class DataFrame:
  def __init__(self):
    self.x = 1

  def __getattr__(self, name):
    current = self.x
    self.x += 1
    return lambda x: x + current
```

Here you can see that 

```python
df = DataFrame()
tail = df.tail
tail(10)
tail(10) #11
```

vs

```python
df = DataFrame()
df.tail(10)
df.tail(10) #12
```

This is pertinant in that we cannot expand `df.tail` to `MethodType(tail, df)` unless we know there are no side effects. This has effects when we compare manifests that are semantically the same, but where we can't assume they are. 

So while we know that `df.tail(10)` will return the same results given the same `DataFrame` the base system can't assume so. Luckily, because Special Eval does incremental evaluation, we can provide this metadata since we know that `df` is `DataFrame`.

I want the base system to be as precise as possible and let the metadata adapters provide clarity. For example, the `pd.core.DataFrame.tail` technically points to `pd.core.generic.NDFrame.tail`. So the question is which one should be the default? I'm leaning towards just the `__self__.__class__`. Going after the `__func__` qualname might be a bit overkill.

### Operation Expansion

```python
df + 1
df.__add__(1)
pd.DataFrame.__add__(df, 1)
```

Those three look the same, but technically the `+` operator will also call `__radd__`. Again, this is one where some kind of MetaData lookup would be able to tell me whether the expressions are equivalent. Otherwise, they have to be treated as different entitites even if they are semantically equivalent.


### getattr

```python
df.tail
getattr(df, 'tail')
getattr(df, 'tail', None)
```

I think that the first two are exactly equivalent. Again, the 3rd one can be rewritten based on metadata.

## DataFrame manifests with deferred operations

```python
from asttools import _eval, _exec
from asttools.eval import _compile

df = pd.DataFrame(np.random.randn(100000, 100))

for x in range(100000):
    df.ix[x] = np.arange(x, x+100)

# 16.9s

# simulate deferring operations

df2 = pd.DataFrame(np.random.randn(100000, 100))

for_text = """
for x in range(100000):
    ops.append((x, np.arange(x, x+100)))
"""

fornode = ast.parse(for_text).body[1]
iter = _eval(fornode.iter, {})
ns = {'df': df2, 'np': np, 'ops': []}
code = _compile(fornode.body[0])
for x in iter:
    ns['x'] = x
    eval(code, ns)

ops = ns['ops']
keys = [x[0] for x in ops]
val = np.vstack([x[1] for x in ops])
df2.ix[keys] = val
# 1.6s

pd.util.testing.assert_frame_equal(df, df2.astype(float)) # note right now df2 is all ints. bug?
```

So that's a bit of a contrived example, though things like that often hit SO. 

I keep on going back and forth on whether I need a special DeferredDataFrame for these types of dynamic operations. I was leaning towards yes when I was considering situations like:

```python
for meth in ['__add__', '__sub__']:
  val = getattr(df, meth)(1)
```

if I were to just execute the for loop itself, I might require a special DataFrame object that can intercept calls made to it and call back to our engine, but 
  
1. that seems intractable as part of the purpose of special eval is giving access to the code interacting with DataFrames and not just using a DeferringDataFrame. The DDF approach works for things I can properly catch like `+`, but I can't catch and defer `pd.rolling_sum`. Now one could make the DDF a subclass of DataFrame and have it evaluate whenever it can't defer, but that kind of misses the point

2. We can parse and run the for loop ourselves. Not only does this keep us from juggling a proxy dataframe object, but it allows us to do the kind of optimizations found above. 

Though to be fair, a deferringdataframe could have done the above optimizations as well. In reality, a lot of the theoretical DDF functionality would be replicated via the special eval incremental eval with a metadata engine, and vice versa. It's just that the special eval stuff is more comprehensive.
