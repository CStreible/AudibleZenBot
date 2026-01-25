using System;
using core.secret_store;

class Program
{
    static int Main(string[] args)
    {
        if (args.Length == 0) {
            Console.Error.WriteLine("Usage: dotnet run -- <secret>");
            return 2;
        }
        var secret = args[0];
        var enc = Secret_storeModule.ProtectString(secret);
        Console.WriteLine(enc);
        return 0;
    }
}
