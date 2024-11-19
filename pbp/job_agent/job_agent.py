

from pathlib import Path
from datetime import date, timedelta, datetime
import os
import time
from loguru import logger  # A great logger option.
import sys

# Configure loguru to print to the terminal
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO")

# Example usage
logger.info("This will be printed directly to the terminal")
    

class JobAgent:
    """This class structure is designed to encapsulate the entire pbp process suite in a simple agent that performs all tasks, more automation with fewer parameters and no URI interface."""

    def __init__(
        self,
        name,  # Name of the deployment
        recorder,  # Recorder type
        audio_base_dir,  # Audio base directory
        json_base_dir,  # JSON base directory
        start,  # Start date
        end,  # End date
        prefix,  # Prefix
        nc_output_dir,  # NetCDF output directory
        global_attrs,  # Global attributes file
        variable_attrs,  # Variable attributes file
        sensitivity_flat_value,  # Sensitivity flat value
        latlon,  # Latitude and Longitude
        title,  # Title
        cmlim,  # CMLIM
        ylim,  # YLIM
        log_dir, # Log directory
        meta_output_dir = None,
        xml_dir = None
    ):
        self.name = name
        if not self.name.endswith('_'):
            self.name += '_'
        if meta_output_dir is None:  # Sets the log directory the same as the json base directory if not specified which feels like a good best practice. 
            meta_output_dir = json_base_dir
            
        self.recorder = recorder
        self.audio_base_dir = audio_base_dir

        if os.name == "nt":
            self.uri = Path(self.audio_base_dir).resolve().as_uri()
            self.meta_output_dir = Path(meta_output_dir)
            self.json_base_dir = Path(json_base_dir)
            self.xml_dir = Path(xml_dir)
            self.nc_output_dir = Path(nc_output_dir)
            self.global_attrs = Path(global_attrs)
            self.variable_attrs = Path(variable_attrs)
            self.log_dir = Path(log_dir)
        if os.name == "posix":
            self.uri = Path(self.audio_base_dir).resolve().as_uri()
            self.meta_output_dir = Path(meta_output_dir).as_posix()
            self.json_base_dir = Path(json_base_dir).as_posix()
            self.xml_dir = Path(xml_dir).as_posix()
            self.nc_output_dir = Path(nc_output_dir).as_posix()
            self.global_attrs = Path(global_attrs).as_posix()
            self.variable_attrs = Path(variable_attrs).as_posix()
            self.log_dir = Path(log_dir).as_posix()

        self.prefix = str(prefix)
        self.start_date = datetime.strptime(start, "%Y%m%d").date()
        self.end_date = datetime.strptime(end, "%Y%m%d").date()

        self.sensitivity_flat_value = str(sensitivity_flat_value)
        self.latlon = latlon
        self.title = title
        self.cmlim = cmlim
        self.ylim = ylim  # YLIM
        #if os.name == "nt":
            #logger.add(log_dir+r"\pbp-job-agent.log")
        #if os.name == "posix":
            #logger.add(log_dir+"/pbp-job-agent.log")
        self.output_prefix = self.name

    def search_filenames(self, directory, pattern):
        try:
            # List all files in the directory
            files = os.listdir(directory)

            # Check if any file contains the pattern
            for file in files:
                if pattern in file:
                    return True
            return False  # Return False if no file contains the pattern
        except FileNotFoundError:
            return False  # Return False if the directory doesn't exist

    def synth_pbp_meta_gen(
        self, recorder, uri, output_dir, json_base_dir, xml_dir, start, end, prefix
    ):
        command = (
            r"pbp-meta-gen "
            + r"--recorder "
            + recorder
            + r" --uri "
            + uri
            + r" --output-dir "
            + output_dir
            + r" --json-base-dir "
            + json_base_dir
            + r" --xml-dir "
            + xml_dir
            + r" --start "
            + start
            + r" --end "
            + end
            + r" --prefix "
            + str(prefix)
        )
        print(command)
        return command

    def synth_pbp_hmb_gen(
        self,
        date,
        json_base_dir,
        audio_base_dir,
        output_dir,
        global_attrs,
        variable_attrs,
        sensitivity_flat_value,
        output_prefix
    ):
        command = (
            r"pbp-hmb-gen --date "
            + date
            + r" --json-base-dir "
            + json_base_dir
            + r" --audio-base-dir "
            + audio_base_dir
            + r" --output-dir "
            + output_dir
            + r" --global-attrs "
            + global_attrs
            + r" --variable-attrs "
            + variable_attrs
            + r" --sensitivity-flat-value "
            + sensitivity_flat_value
            + r" --output-prefix "
            + output_prefix
        )
        return command

    def synth_pbp_plot_gen(self, latlon, title, cmlim, ylim, nc_file):
        command = (
            r"pbp-hmb-plot --latlon "
            + latlon
            + r" --title "
            + title
            + r" --cmlim "
            + cmlim
            + r" --ylim "
            + ylim
            + r" "
            + nc_file
        )
        return command

    def run(self):
        logger.opt(colors=True).info(
            "<blue>Initializing the pbp/pypam processing suite.</blue>"
        )

        """Metadata generation and logs"""

        command = self.synth_pbp_meta_gen(
            self.recorder,
            self.uri,
            self.meta_output_dir,
            self.json_base_dir,
            self.xml_dir,
            self.start_date.strftime("%Y%m%d"),
            self.end_date.strftime("%Y%m%d"),
            self.prefix,
        )
        logger.opt(colors=True).info(
            "<blue>Initiating processing for audio file and netCDF generation associated with : "
            + str(self.start_date)
            + "</blue>"
        )
        logger.opt(colors=True).info("<green>running > " + command + "</green>")
        os.system(command)

        delta = timedelta(days=1)
        command = ""

        while self.start_date <= self.end_date:
            try:
                """NetCDF generation and logs"""

                logger.opt(colors=True).info(
                    "<blue>Initiating pypam/pbp processing sequence for audio file associated with : "
                    + str(self.start_date)
                    + "</blue>"
                )
                logger.opt(colors=True).info(
                    "<blue>Initiating metadata generation associated with : "
                    + str(self.start_date)
                    + "</blue>"
                )

                command = self.synth_pbp_hmb_gen(
                    date=self.start_date.strftime("%Y%m%d"),
                    json_base_dir=self.json_base_dir,
                    audio_base_dir=self.audio_base_dir,
                    output_dir=self.nc_output_dir,
                    global_attrs=self.global_attrs,
                    variable_attrs=self.variable_attrs,
                    sensitivity_flat_value=self.sensitivity_flat_value,
                    output_prefix = self.output_prefix
                )
                logger.opt(colors=True).info(
                    "<blue>Checking if netCDF file associated with "
                    + str(self.start_date.strftime("%Y%m%d"))
                    + " exists...</blue>"
                )
                if not self.search_filenames(
                    self.nc_output_dir, str(self.start_date.strftime("%Y%m%d")) + ".nc"
                ):
                    logger.opt(colors=True).info(
                        "<blue>No netCDF file exists for "
                        + str(self.start_date) + ". Proceeding to netCDF generation of "+str(self.start_date)+"."
                        + "</blue>"
                    )
                    logger.opt(colors=True).info(
                        "<blue>Proceeding to netCDF generatrion...</blue>"
                    )
                    logger.opt(colors=True).info(
                        "<green>running > " + command + "</green>"
                    )
                    
                    os.system(command)
                    
                    logger.opt(colors=True).info(
                        "<blue>NetCDF file generation for "
                        + str(self.start_date)
                        + " complete!</blue>"
                    )
                else:
                    logger.opt(colors=True).info(
                        "<yellow>NetCDF file already exists for "
                        + str(self.start_date)
                        + "</yellow>"
                    )

                """NetCDF Plotting"""
                command = ""  # Reset command
                if os.name == "nt":  # For Windows-based systems
                    command = self.synth_pbp_plot_gen(
                        latlon=self.latlon,
                        title=self.title,
                        cmlim=self.cmlim,
                        ylim=self.ylim,
                        nc_file=os.path.join(self.nc_output_dir, "milli_psd_", str(self.start_date.strftime("%Y%m%d")) + ".nc"),

                    )  # Generate the command for plotting the NetCDF file
                if os.name == "posix":  # For Unix-based systems
                    command = self.synth_pbp_plot_gen(
                        latlon=self.latlon,
                        title=self.title,
                        cmlim=self.cmlim,
                        ylim=self.ylim,
                        nc_file=os.path.join(self.nc_output_dir, self.name+str(self.start_date.strftime("%Y%m%d")) + ".nc"),
                    )  # Generate the command for plotting the NetCDF file

                logger.opt(colors=True).info(
                    "<blue>Initiating plot generation for audio file associated with date : "
                    + str(self.start_date)
                    + "</blue>"
                )
                logger.opt(colors=True).info(
                    "<blue>Checking if jpg file associated with "
                    + str(self.start_date)
                    + " exists...</blue>"
                )
                if not self.search_filenames(
                    self.nc_output_dir, str(self.start_date.strftime("%Y%m%d")) + ".jpg"
                ):
                    logger.opt(colors=True).info(
                        "<blue>No plot exists or has been generated for the date: "
                        + str(self.start_date)
                        + "</blue>"
                    )
                    logger.opt(colors=True).info(
                        "<blue>Proceeding to plot generatrion from netCDF...</blue>"
                    )
                    logger.opt(colors=True).info(
                        "<green>running > " + command + "</green>"
                    )
                    os.system(command)
                else:
                    logger.opt(colors=True).info(
                        "<yellow>Plot already exists for "
                        + str(self.start_date)
                        + "</yellow>"
                    )
                    logger.opt(colors=True).info(
                        "<yellow>Perfroming an override of the existing plot for "
                        + str(self.start_date)
                        + "</yellow>"
                    )
                    logger.opt(colors=True).info(
                        "<green>running > " + command + "</green>"
                    )
                    os.system(command)
                    logger.opt(colors=True).info(
                    "<blue>Plot generation complete!</blue>"
                )

                self.start_date += delta  # Iterate to next day.
                logger.opt(colors=True).info(
                    "<blue>Proceeding to the next day for processing...</blue>"
                )
                time.sleep(1)

            except TypeError as e:
                logger.error(f"Processing was unsuccessful for {self.start_date} at line {sys.exc_info()[-1].tb_lineno}")
                logger.error(f"Error: {e}")
                print(f"Error: {e} at line {sys.exc_info()[-1].tb_lineno}")