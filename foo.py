from wakepy import keep

print("global")
with keep.running() as mode:
    ...


def first():
    with keep.running():
        ...


@keep.running
def second(): ...


@keep.running()
def third(): ...


print("\nfirst")
first()
print("\nsecond")
second()
print("\nthird")
third()
