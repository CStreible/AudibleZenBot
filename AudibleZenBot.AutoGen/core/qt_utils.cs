using System;
using System.Threading.Tasks;

namespace core.qt_utils {
    public static class Qt_utilsModule {
        // Original: def __init__(self, parent=None)
        public static void Init(object? parent = null) {
            // TODO: implement
        }

        // Original: def _call(self, func, args, kwargs)
        public static void Call(object? func, object? args, object? kwargs) {
            // TODO: implement
        }

        // Original: def get_main_thread_executor(parent=None)
        public static void GetMainThreadExecutor(object? parent = null) {
            // TODO: implement
        }

    }

    public class MainThreadExecutor {
        public object? run { get; set; }


        // Original: def __init__(self, parent=None)
        public MainThreadExecutor(object? parent = null) {
            // TODO: implement constructor
            this.run = null;
        }

        // Original: def _call(self, func, args, kwargs)
        public void Call(object? func, object? args, object? kwargs) {
            // TODO: implement
        }

        // Original: def get_main_thread_executor(parent=None)
        public void GetMainThreadExecutor(object? parent = null) {
            // TODO: implement
        }

    }

}

