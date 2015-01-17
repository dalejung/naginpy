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
