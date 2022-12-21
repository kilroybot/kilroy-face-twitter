# Processors

Processors are a way to handle different types of messages.
They are able to convert between
internal and external representations of messages.

There are multiple types of processors available,
each supporting a different type of message:

- `TextOnlyProcessor`
- `ImageOnlyProcessor`
- `TextAndImageProcessor`
- `TextOrImageProcessor`
- `TextWithOptionalImageProcessor`
- `ImageWithOptionalTextProcessor`

You can set the processor to use in the initial configuration,
but you can't change the type of processor at runtime.
