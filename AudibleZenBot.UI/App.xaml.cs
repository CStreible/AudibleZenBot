using System;
using System.Collections.Generic;
using System.Configuration;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;

namespace AudibleZenBot.UI
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);
            AppDomain.CurrentDomain.UnhandledException += (s, ex) => {
                try { System.IO.File.AppendAllText("audiblezenbot_crash.log", DateTime.UtcNow + " UnhandledException: " + ex.ToString() + "\n"); } catch { }
            };
            this.DispatcherUnhandledException += (s, ex) => {
                try { System.IO.File.AppendAllText("audiblezenbot_crash.log", DateTime.UtcNow + " DispatcherUnhandledException: " + ex.Exception.ToString() + "\n"); } catch { }
                ex.Handled = false;
            };
            TaskScheduler.UnobservedTaskException += (s, ex) => {
                try { System.IO.File.AppendAllText("audiblezenbot_crash.log", DateTime.UtcNow + " UnobservedTaskException: " + ex.Exception.ToString() + "\n"); } catch { }
            };
            try { System.IO.Directory.CreateDirectory(".audiblezenbot\logs"); } catch { }
        }
    }
}
