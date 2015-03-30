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

03-30-15

# reactive-ish

I'm not 100% on the terminology. But if you imagine a world where arrays are viewed as immutable streams of events. Then each stream input can be versionined. Now then imagine that all operations on such streams know how to handle streams as both events and arrays. If both these things are true, then something like this:

```python
positive_sum_30 = frp.rolling(30).filter(lambda x: x > 0).sum()
```

Can be viewed as both a vector and live system. `positive_sum_30` is itself a TimeSeries, sliding window func, a live system. Or at least it should be. You should be able to pulse that system with an Event and get that aggregate system back. If you have the whole array, you should be able to run this at the same speed as normal vectorized funcs. At that point, it should be able to be turned live. These systems should be able to store state as well.

Take something like a system that is current to yesterdays data. 

```python

# versioned data
data = History('AAPL')
stale_data = data.ix[:"2015-03-25"]
new_data = data.ix["2015-03-25":]

positive_sum_30 = frp.rolling(30).filter(lambda x: x > 0).sum()

psum = positive_sum_30.copy()

test1 = psum(stale_data)

psum2 = positive_sum_30.copy()
test2 = []
for evt in stale_data:
  out = psum2(evt)
  test2.append(out)

# since History returns an immutable versioned stream
assert test1 == test2

# whatever internal bookkeeping needed should be the same
# for something like this, the only internal state would be the current sum and the last 30.
# something interesting is that if you have access to the entire array, you don't keep the last 30
# you just see what's leaving the window by offset.
# so its state would be derived.
assert psum.state == psum2.state
```

Now, since the data is versioned. Systems that are up to date to a certain time can all be interchanged regardless of how you got there. You could:

1. persisted the system at t
2. Take a system persisted at t-n and then playback events till t
3. Take a blank system and send an array of 0->t
4. Take a system at t-n, and send an array of data for t-n->t

Note that the idea is to be able to have multiple correct implementations for the same "system". In that way we view computation like transducer in that they are a process. Imagine that you split up each component into message sending components using rabbitmq. So Rolling would keep the data buffer and either send window slices, or send the events with some type of end event for the window, filter would either gate the events or just send the bool. Now the quesiton is, does the above system sum the wihndow, or wait for 30 values. obv in this case that it is each window. So filter itself would need to send some sort of end. Then sum would sum and we'd aggregate that output on some other listener.

So even in the message sending layout, where we really can't use intermediate values to speed up computation since there is process isolation, there are different implementations. Do we send whole window slices of data, or send reactive type event streams. Both of them would need some sort of ID/offset so the result aggregate could order them since there's no expectation of ordering this model. Also, note that you could have split the components into any configuration of meta components i.e. put filter/sum into the same component.

Outside of some sort of usefulness, one of the reason for this write once use anywhere is that they can be tested against each other. If we have production systems, we can test the output series against each other by switching flags. Even if we are given an array of data, there is no reason we couldn't break that up into events that feed into a live algo or networked system of components. If there's deviation based on conveyance, then we can't test.

This all goes in line with the simple dumb case of having some aggregate statistics, pushing a button to add it to a dashboard, and having it automatically update with new data.

# composability

So one of the nice things about viewing things functional is the lack of side effects here and composability. This gives us so much flexibility in building out equivalent systems.

```
statA = frp.rolling(30).slow_stat1()
statB = frp.rolling(30).slow_stat2()

signal = frp.crossover(statA > statB)
```

Note that signal itself is just another system. Let's imagine that `slow_stat` is compute intensive. We might want to separate it to it's own CPU. Because everything is pure, we could take the internal system which would be closer to:

```
Crossover
  Rolling
    slow_stat1
    slow_stat2
```

To something like
```
Rolling
  slow_stat1

Rolling
  slow_stat2

Crossover
```

Which would be 3 components. I wonder if it's possible to have it be more crazy like:


```
Crossover
  Rolling
    slow_stat1

Rolling
  slow_stat2
```

Where one stat is computed locally and we wait for the other event to test signal. Seems like it should be fine...

Also of note, due to pureness we can swap out sections of the compute graph for optimized versions. A good example re the rolling window functions which usually have a intermediate accounting speed up. So we could easily replace
`rolling(30).mean()` with `RollingMean(30)` which wouldn't re-sum across the window.

Again, these different configurations are all meant to be equivalent, so they can be tested against each other. And each part can be switch out.

The above crossover example is interesting. Crossover has two inputs streams. Can one be wired up to be an array and the other an event listener? Either way, the evented objects would have the streams ID and offset so they could be matched up. I suppose in that sense, the Crossover would default to live, and then just treat the array ihput as an event source.

Which brings up bouncebox, previous I had done stuff with this where you could subscribe to all events, event types, or a specific stream. Which actually is essentially like reactive streams. I have to go see whether I made it a requirement that you specify the stream first. Essentially for somethign like crossover, you'd have to give it stream object that was revisionable. Back then I didn't know what this type of stuff was called.
