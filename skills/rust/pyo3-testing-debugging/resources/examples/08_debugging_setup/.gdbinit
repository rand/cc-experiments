# GDB configuration for PyO3 debugging

# Enable Python pretty printing
python
import sys
sys.path.insert(0, '/usr/share/gdb/python')
from gdb import printing
end

# Set breakpoint commands
define pyo3_break
    break $arg0
    commands
        silent
        backtrace
        info locals
        continue
    end
end

# Rust panic handling
catch throw
catch signal SIGSEGV

# Display settings
set print pretty on
set print object on
set print static-members on
set print vtbl on
set print demangle on
set demangle-style gnu-v3

# History
set history save on
set history size 10000
set history filename ~/.gdb_history
