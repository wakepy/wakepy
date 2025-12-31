(multithreading-multiprocessing)=
# Multithreading and multiprocessing safety

## General guidelines
- Every [Wakepy Method](#wakepy-methods) is multiprocessing and multithreading safe. Wakepy by default does not alter any settings or have such side effects that would make it not possible have multiple wakepy Modes (inhibitors) active at the same time.
- It is _not_ safe to share {class}`Mode <wakepy.Mode>` instances between threads (the ones returned by {func}`keep.running() <wakepy.keep.running>` and {func}`keep.presenting() <wakepy.keep.presenting>`)
- It _is_ safe to share the functions decorated with wakepy factory functions 
  with multiple threads, as each of them creates a new {class}`Mode <wakepy.Mode>` internally.

## Examples

### Examples of safe usage
These are multithreading and multiprocessing safe ways using wakepy:

```{code-block} python

# Thread-safe because the decorated function long_running_function
# will create new Mode instance on every call.

@keep.running
def long_running_function(n):
    USER_CODE
```

```{code-block} python
# Also thread safe. Same reasons as above

@keep.running()
def long_running_function():
    USER_CODE

```

```{code-block} python

# Thread safe because each thread will get it's own Mode instance
# From keep.running()

def long_running_function(n):
    with keep.running():
        USER_CODE
```

### Unsafe usage

Any usage pattern sharing a {class}`Mode <wakepy.Mode>` instance between threads is unsafe. The following is *ok* for single-threaded code, but ***not ok*** if `long_running_function` is running on a separate thread.

```{code-block} python

# Creating Mode instance on one thread
keepawake = keep.running()

@keepawake
def long_running_function():
    # UNSAFE! Using the Mode instance in separate thread
    print(f'Using: {keepawake.method}')

```

```{seealso}
{func}`~wakepy.current_mode` would be the correct way for getting the current Mode instance in a thread-safe way.
```
