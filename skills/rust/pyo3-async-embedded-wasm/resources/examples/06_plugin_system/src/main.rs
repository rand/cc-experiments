use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::path::PathBuf;

struct PluginManager {
    plugins: HashMap<String, Py<PyAny>>,
}

impl PluginManager {
    fn new() -> Self {
        pyo3::prepare_freethreaded_python();
        Self {
            plugins: HashMap::new(),
        }
    }

    fn load_plugin(&mut self, name: String, path: PathBuf) -> PyResult<()> {
        Python::with_gil(|py| {
            let code = std::fs::read_to_string(&path)?;
            let module = PyModule::from_code(py, &code, &path.to_str().unwrap(), &name)?;

            let plugin_class = module.getattr("Plugin")?;
            let plugin_instance = plugin_class.call0()?;

            self.plugins.insert(name, plugin_instance.into());
            Ok(())
        })
    }

    fn call_plugin(&self, name: &str, method: &str, args: Vec<i64>) -> PyResult<i64> {
        Python::with_gil(|py| {
            let plugin = self.plugins.get(name)
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                    format!("Plugin not found: {}", name)
                ))?;

            let result = plugin.call_method1(py, method, (args,))?;
            result.extract(py)
        })
    }

    fn list_plugins(&self) -> Vec<String> {
        self.plugins.keys().cloned().collect()
    }
}

fn main() -> PyResult<()> {
    println!("Plugin System Example\n");

    let mut manager = PluginManager::new();

    // Create example plugin
    let plugin_code = r#"
class Plugin:
    def __init__(self):
        self.name = "example_plugin"

    def process(self, data):
        return sum(data)

    def transform(self, data):
        return [x * 2 for x in data]
"#;
    std::fs::write("example_plugin.py", plugin_code)?;

    // Load plugin
    println!("Loading plugin...");
    manager.load_plugin("example".to_string(), "example_plugin.py".into())?;

    // Call plugin
    println!("Calling plugin methods:");
    let sum = manager.call_plugin("example", "process", vec![1, 2, 3, 4, 5])?;
    println!("  Sum: {}", sum);

    println!("\nLoaded plugins: {:?}", manager.list_plugins());

    // Cleanup
    std::fs::remove_file("example_plugin.py").ok();

    Ok(())
}
