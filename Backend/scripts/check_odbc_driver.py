import pyodbc

drivers = pyodbc.drivers()

print("Installed 64-bit ODBC drivers:")
for driver in drivers:
    print(" -", driver)

oracle = [d for d in drivers if "oracle" in d.lower()]

if oracle:
    print("\nOracle ODBC driver detected:")
    for driver in oracle:
        print(" -", driver)
else:
    print(
        "\nNo Oracle ODBC driver was detected. Install the 64-bit Oracle "
        "Instant Client Basic package plus the matching ODBC package, "
        "then configure a 64-bit DSN."
    )
