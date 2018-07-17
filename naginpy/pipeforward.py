"""
df = value %>%
    sum %>%
    filter(is_na) %>%
    summarize

df = value |> 
    sum |> 
    filter(is_na) |>
    summarize

with PipeForward(value) as df:
    _ = value
    _ = sum(_)
    _ = filter(_, is_na)
    _ = summarize(_)
    df = _

with PipeForward(value):
    sum
    filter(10)
    summarize


with value.pipe():
    
"""
with value.pipe():
    sum #>>
    filter(10) #>>
    summarize

value >> sum
