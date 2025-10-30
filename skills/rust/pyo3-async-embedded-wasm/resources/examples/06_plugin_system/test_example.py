"""
This example is a Rust binary that embeds Python.
Run with: cargo run

This file demonstrates what the plugin system does.
"""

def demonstrate_plugin():
    """Example plugin that would be loaded by Rust"""

    class Plugin:
        def __init__(self):
            self.name = "example_plugin"

        def process(self, data):
            """Process data - sum all values"""
            return sum(data)

        def transform(self, data):
            """Transform data - multiply by 2"""
            return [x * 2 for x in data]

    plugin = Plugin()
    print(f"Plugin: {plugin.name}")
    print(f"Process [1,2,3,4,5]: {plugin.process([1,2,3,4,5])}")
    print(f"Transform [1,2,3]: {plugin.transform([1,2,3])}")


if __name__ == "__main__":
    print("Plugin System Demonstration")
    print("Run the actual example with: cargo run\n")
    demonstrate_plugin()
