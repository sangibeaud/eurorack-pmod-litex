#!/usr/bin/env python3

# This variable defines all the external programs that this module
# relies on.  lxbuildenv reads this variable in order to ensure
# the build will finish without exiting due to missing third-party
# programs.
#LX_DEPENDENCIES = ["riscv", "nextpnr-ecp5", "yosys"]
LX_DEPENDENCIES = ["riscv", "vivado", "yosys"]

# Import lxbuildenv to integrate the deps/ directory
import lxbuildenv

from litex.build.generic_platform import *
from litex.build.xilinx import *

from litex_boards.platforms import qmtech_kintex7_devboard
from litex.build.xilinx.vivado import vivado_build_args, vivado_build_argdict

from litex.soc.cores.clock import *
from litex.soc.cores.dma import *
from litex.soc.interconnect import wishbone
from litex.soc.interconnect.stream import ClockDomainCrossing
from litex.soc.interconnect.csr_eventmanager import *

from litex_boards.targets.qmtech_kintex7_devboard import *

from rtl.eurorack_pmod_wrapper import *
from rtl.dsp_wrapper import *
from rtl.dma_router import *

_io_eurorack_pmod = [
    ("eurorack_pmod_p0", 0,
#        Subsignal("mclk",    Pins("W26")),
        Subsignal("mclk",    Pins("J11:1")),
#        Subsignal("pdn",     Pins("V26")),
        Subsignal("pdn",     Pins("J11:2")),
#        Subsignal("i2c_sda", Pins("U26")),
        Subsignal("i2c_sda", Pins("J11:3")),
#        Subsignal("i2c_scl", Pins("T26")),
        Subsignal("i2c_scl", Pins("J11:4")),
#        Subsignal("sdin1",   Pins("T25")),
        Subsignal("sdin1",   Pins("J11:7")),
#        Subsignal("sdout1",  Pins("U25")),
        Subsignal("sdout1",  Pins("J11:8")),
#        Subsignal("lrck",    Pins("U24")),
        Subsignal("lrck",    Pins("J11:9")),
#        Subsignal("bick",    Pins("V24")),
        Subsignal("bick",    Pins("J11:10")),
        IOStandard("LVCMOS33")
    ),
]

# PMOD_1
#    ("J11", {
#      1: "C16", 7: "B16",
#      2: "A17", 8: "B17",
#      3: "A18", 9: "A19",
#      4: "A20", 10: "B20", 
#    }),

def add_eurorack_pmod(soc, sample_rate=48000, dma_output_capable=True):
    soc.platform.add_extension(_io_eurorack_pmod)

    # Create 256*Fs clock domain
    soc.crg.clock_domains.cd_clk_256fs = ClockDomain()
    soc.crg.pll.create_clkout(soc.crg.cd_clk_256fs, sample_rate * 256)

    # Create 1*Fs clock domain using a division register
    soc.crg.clock_domains.cd_clk_fs = ClockDomain()
    clkdiv_fs = Signal(8)
    soc.sync.clk_256fs += clkdiv_fs.eq(clkdiv_fs+1)
    soc.comb += soc.crg.cd_clk_fs.clk.eq(clkdiv_fs[-1])

    # Now instantiate a EurorackPmod.
    eurorack_pmod_pads = soc.platform.request("eurorack_pmod_p0")
    eurorack_pmod = EurorackPmod(soc.platform, eurorack_pmod_pads)
    soc.add_module("eurorack_pmod0", eurorack_pmod)

    # Now instantiate the DMA router and connect it to the EurorackPmod.
    add_dma_router(soc, eurorack_pmod, output_capable=dma_output_capable)

def main():
    from litex.build.parser import LiteXArgumentParser
    #parser = LiteXArgumentParser(platform=lambdaconcept_ecpix5.Platform, description="LiteX SoC on ECPIX-5.")
    #parser.add_target_argument("--device",          default="85F",            help="ECP5 device (45F or 85F).")
    #parser.add_target_argument("--sys-clk-freq",    default=100e6, type=float, help="System clock frequency.")

    parser = argparse.ArgumentParser(description="LiteX SoC on QMTech XC7K325T")
    parser.add_argument("--toolchain",           default="vivado",                 help="FPGA toolchain (vivado, symbiflow or yosys+nextpnr).")
    parser.add_argument("--build",               action="store_true",              help="Build bitstream.")
    parser.add_argument("--load",                action="store_true",              help="Load bitstream.")
    parser.add_argument("--sys-clk-freq",        default=100e6,                    help="System clock frequency.")
    ethopts = parser.add_mutually_exclusive_group()
    ethopts.add_argument("--with-ethernet",      action="store_true",              help="Enable Ethernet support.")
    ethopts.add_argument("--with-etherbone",     action="store_true",              help="Enable Etherbone support.")
    parser.add_argument("--eth-ip",              default="192.168.1.50", type=str, help="Ethernet/Etherbone IP address.")
    parser.add_argument("--eth-dynamic-ip",      action="store_true",              help="Enable dynamic Ethernet IP addresses setting.")
    parser.add_argument("--remote-ip",           default="192.168.1.100",
   help="Remote IP address of TFTP server.")
    parser.add_argument("--local-ip",            default="192.168.1.50",
   help="Local IP address.")
    sdopts = parser.add_mutually_exclusive_group()
    sdopts.add_argument("--with-spi-sdcard",     action="store_true",              help="Enable SPI-mode SDCard support.")
    sdopts.add_argument("--with-sdcard",         action="store_true",              help="Enable SDCard support.")
    parser.add_argument("--with-spi-flash",      action="store_true",              help="Enable SPI Flash (MMAPed).")
    viopts = parser.add_mutually_exclusive_group()
    viopts.add_argument("--with-video-terminal",    action="store_true", help="Enable Video Terminal (VGA).")
    viopts.add_argument("--with-video-framebuffer", action="store_true", help="Enable Video Framebuffer (VGA).")
    viopts.add_argument("--with-video-colorbars", action="store_true", help="Enable Video Colorbars (VGA).")
    builder_args(parser)
    soc_core_args(parser)
    vivado_build_args(parser)
    
    args = parser.parse_args()

    soc = BaseSoC(
        toolchain              = args.toolchain,
        sys_clk_freq           = int(float(args.sys_clk_freq)),
        with_ethernet          = args.with_ethernet,
        with_etherbone         = args.with_etherbone,
        eth_ip                 = args.eth_ip,
        eth_dynamic_ip         = args.eth_dynamic_ip,
        local_ip               = args.local_ip,
        remote_ip              = args.remote_ip,
        with_spi_flash         = args.with_spi_flash,
        with_video_terminal    = args.with_video_terminal,
        with_video_framebuffer = args.with_video_framebuffer,
        with_video_colorbars = args.with_video_colorbars,
        **soc_core_argdict(args)
    )


#    soc = BaseSoC(
#        device                 = args.device,
#        sys_clk_freq           = args.sys_clk_freq,
#        toolchain              = args.toolchain,
#        **parser.soc_argdict
#    )

    add_eurorack_pmod(soc)

    #builder = Builder(soc, **parser.builder_argdict)
    #if args.build:
    #    builder.build(**parser.toolchain_argdict)

    builder = Builder(soc, **builder_argdict(args))
    if args.with_ethernet or args.with_etherbone:
        os.makedirs(os.path.join(builder.software_dir, "include/generated"),
                    exist_ok=True)
        write_to_file(
            os.path.join(builder.software_dir, "include/generated", "target.h"),
            "// Force 100Base-T speed\n"
            "#define TARGET_ETHPHY_INIT_FUNC() mdio_write(0, 0, 0x2100)")
    
    builder_kwargs = vivado_build_argdict(args) if args.toolchain == "vivado" else {}
    if args.build:
	    builder.build(**builder_kwargs)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
