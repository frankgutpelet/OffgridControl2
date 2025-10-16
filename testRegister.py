from pymodbus.client import ModbusSerialClient

class GrowattConsole:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, unit=1):
        self.client = ModbusSerialClient(
            port=port,
            framer="rtu",
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
        )
        self.unit = unit

    def read_register(self, addr, count=1):
        try:
            result = self.client.read_input_registers(address=addr, count=count, slave=self.unit)
            if result.isError():
                print(f"Error reading register {addr}")
                return None
            return result.registers
        except Exception as e:
            print(f"Exception reading register {addr}: {e}")
            return None

    def read_32bit(self, addr):
        regs = self.read_register(addr, count=2)
        if not regs or len(regs) < 2:
            return None
        return self.client.convert_from_registers(
            regs,
            data_type=self.client.DATATYPE.UINT32,
        )

    def run_console(self):
        if not self.client.connect():
            print("❌ Connection failed")
            return

        print(" Connected to Growatt Inverter Console")
        print("Type 'q' to quit.")
        print("Usage: Enter register number, optionally add '32' for 32-bit (e.g. '5 32').\n")

        try:
            while True:
                cmd = input("Register> ").strip()
                if cmd.lower() in ["q", "quit", "exit"]:
                    break

                parts = cmd.split()
                if not parts:
                    continue

                try:
                    addr = int(parts[0])
                except ValueError:
                    print("⚠️ Please enter a valid register number.")
                    continue

                is32 = len(parts) > 1 and parts[1] == "32"

                if is32:
                    val = self.read_32bit(addr)
                    print(f"Reg[{addr}/{addr+1}] (32-bit) = {val}")
                else:
                    val = self.read_register(addr)
                    if val is not None:
                        print(f"Reg[{addr}] = {val[0]}")
        finally:
            self.client.close()
            print("Connection closed.")


if __name__ == "__main__":
    console = GrowattConsole(port="/dev/ttyUSB0", baudrate=9600, unit=1)
    console.run_console()
