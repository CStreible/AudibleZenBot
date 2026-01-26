using System;
using System.Threading;
using System.Threading.Tasks;
using Xunit;

namespace AudibleZenBot.Tests {
    public class ConnectionsUiTests {
        [Fact]
        public void AddTags_GetTagsAsString_ReturnsCommaSeparated()
        {
            string result = null;
            var done = new ManualResetEventSlim(false);

            var t = new Thread(() => {
                try {
                    // Create the WPF control on STA thread
                    var panel = new AudibleZenBot.WPF.Views.PlatformConnectionPanel();
                    panel.AddTag("one");
                    panel.AddTag("two");
                    result = panel.GetTagsAsString();
                } catch (Exception ex) {
                    result = "ERROR:" + ex.Message;
                } finally {
                    done.Set();
                }
            });
            t.SetApartmentState(ApartmentState.STA);
            t.IsBackground = true;
            t.Start();
            if (!done.Wait(TimeSpan.FromSeconds(5))) throw new TimeoutException("UI thread did not complete in time");

            Assert.Equal("one,two", result);
        }
    }
}
