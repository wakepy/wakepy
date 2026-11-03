(multithreading-multiprocessing)=
# Multithreading and multiprocessing safety

## General guidelines
- Every [Wakepy Method](#wakepy-methods) is multiprocessing and multithreading safe. Wakepy by default does not alter any settings or have such side effects that would make it not possible have multiple wakepy Modes (inhibitors) active at the same time.
- Explicit `Mode.enter()` / `Mode.exit()` calls on a shared instance are serialized, including lifecycle hooks. Entry and exit may occur on different threads. These calls control one shared activation; they do not give each caller an independent lifetime.
- A Mode context has one owner. Use separate instances for overlapping `with` blocks across threads; duplicate context entry raises `ContextAlreadyEnteredError` without changing the original activation. Exit a context on the thread that entered it.
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

Reading the decorator template's state does not inspect its per-call activation. Use `current_mode()` inside the decorated function instead:

```{code-block} python

# Creating Mode instance on one thread
keepawake = keep.running()

@keepawake
def long_running_function():
    # The template is not the Mode created for this invocation.
    print(f'Using: {keepawake.method}')

```

```{seealso}
{func}`~wakepy.current_mode` would be the correct way for getting the current Mode instance in a thread-safe way.
```
