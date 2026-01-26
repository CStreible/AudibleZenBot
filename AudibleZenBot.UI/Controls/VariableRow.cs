using System;
using System.Windows.Forms;

namespace AudibleZenBot.UI.Controls
{
    public class VariableRow : UserControl
    {
        public TextBox NameBox { get; private set; }
        public TextBox ValueBox { get; private set; }
        public TextBox DefaultBox { get; private set; }
        public ComboBox TypeCombo { get; private set; }
        public CheckBox InitCheck { get; private set; }

        public VariableRow()
        {
            InitializeComponents();
        }

        private void InitializeComponents()
        {
            this.Height = 80;
            this.Dock = DockStyle.Top;

            NameBox = new TextBox() { Left = 10, Top = 8, Width = 180, PlaceholderText = "Name" };
            TypeCombo = new ComboBox() { Left = 200, Top = 8, Width = 100, DropDownStyle = ComboBoxStyle.DropDownList };
            TypeCombo.Items.AddRange(new object[] { "string", "int", "float", "bool" });
            TypeCombo.SelectedIndex = 0;

            ValueBox = new TextBox() { Left = 310, Top = 8, Width = 220, PlaceholderText = "Value" };
            DefaultBox = new TextBox() { Left = 540, Top = 8, Width = 150, PlaceholderText = "Default" };

            InitCheck = new CheckBox() { Left = 700, Top = 10, Width = 100, Text = "Initialize" };

            this.Controls.Add(NameBox);
            this.Controls.Add(TypeCombo);
            this.Controls.Add(ValueBox);
            this.Controls.Add(DefaultBox);
            this.Controls.Add(InitCheck);
        }

        public (string name, string type, string value, string def, bool init) GetData()
        {
            return (NameBox.Text ?? string.Empty, TypeCombo.SelectedItem?.ToString() ?? "string", ValueBox.Text ?? string.Empty, DefaultBox.Text ?? string.Empty, InitCheck.Checked);
        }
    }
}
