import pathlib

# from multiprocessing import Pool
from typing import List, Optional, Tuple

# import numpy as np
import soundfile as sf

from src import get_cpus_to_use, save_csv, save_netcdf

from src.file_helper import FileHelper
from src.misc_helper import gen_hour_minute_times, info, warn
from src.pypam_support import PypamSupport


VOLTAGE_MULTIPLIER = 3


class ProcessHelper:
    def __init__(
        self,
        file_helper: FileHelper,
        output_dir: str,
        gen_csv: bool,
        save_segment_result: bool = False,
        save_extracted_wav: bool = False,
        num_cpus: int = 0,
        max_segments: int = 0,
    ):
        self.file_helper = file_helper
        self.output_dir = output_dir
        self.gen_csv = gen_csv
        self.save_segment_result = save_segment_result
        self.save_extracted_wav = save_extracted_wav
        self.num_cpus = get_cpus_to_use(num_cpus)
        self.max_segments = max_segments

        # obtained once upon first segment to be processed
        self.pypam_support: Optional[PypamSupport] = None

        pathlib.Path(output_dir).mkdir(exist_ok=True)

    def process_day(self, year: int, month: int, day: int) -> Optional[str]:
        """
        :param year:
        :param month:
        :param day:
        :return: The path of the generated NetCDF file, or None if no segments were processed.
        """
        if not self.file_helper.select_day(year, month, day):
            return None

        at_hour_and_minutes: List[Tuple[int, int]] = list(
            gen_hour_minute_times(self.file_helper.segment_size_in_mins)
        )

        if self.max_segments > 0:
            at_hour_and_minutes = at_hour_and_minutes[: self.max_segments]
            info(f"NOTE: Limiting to {len(at_hour_and_minutes)} segments ...")

        if self.num_cpus > 1:
            # TODO appropriate dispatch to then aggregate results
            info("NOTE: ignoring multiprocessing while completing aggregation of day")
            # splits = np.array_split(at_hour_and_minutes, self.num_cpus)
            # info(
            #     f"Splitting {len(at_hour_and_minutes)} segments into {len(splits)} processes ..."
            # )
            # with Pool(self.num_cpus) as pool:
            #     args = [(s,) for s in splits]
            #     pool.starmap(self.process_hours_minutes, args)
            # return

        self.process_hours_minutes(at_hour_and_minutes)
        if self.pypam_support is None:
            warn("No segments processed, nothing to aggregate.")
            return None

        info("Aggregating results ...")
        aggregated_result = self.pypam_support.get_aggregated_milli_psd()
        basename = f"{self.output_dir}/milli_psd_{year:04}{month:02}{day:02}"
        nc_filename = f"{basename}.nc"
        save_netcdf(aggregated_result, nc_filename)
        if self.gen_csv:
            save_csv(aggregated_result, f"{basename}.csv")

        self.file_helper.day_completed()

        return nc_filename

    def process_hours_minutes(self, hour_and_minutes: List[Tuple[int, int]]):
        info(f"Processing {len(hour_and_minutes)} segments ...")
        for at_hour, at_minute in hour_and_minutes:
            self.process_segment_at_hour_minute(at_hour, at_minute)

    def process_segment_at_hour_minute(self, at_hour: int, at_minute: int):
        file_helper = self.file_helper
        year, month, day = file_helper.year, file_helper.month, file_helper.day

        info(f"Segment at {at_hour:02}h:{at_minute:02}m ...")
        info(f"  - extracting {file_helper.segment_size_in_mins * 60}-sec segment:")
        extraction = file_helper.extract_audio_segment(at_hour, at_minute)
        if extraction is None:
            warn(f"cannot get audio segment at {at_hour:02}:{at_minute:02}")
            return

        audio_info, audio_segment = extraction

        if self.pypam_support is None:
            # TODO capture subset_to and/or band from command line.
            self.pypam_support = PypamSupport(
                audio_info.samplerate, subset_to=(10, 100_000)
            )
        elif self.pypam_support.fs != audio_info.samplerate:
            info(
                f"ERROR: samplerate changed from {self.pypam_support.fs} to {audio_info.samplerate}"
            )
            return

        if self.save_extracted_wav:
            wav_filename = f"{self.output_dir}/extracted_{year:04}{month:02}{day:02}_{at_hour:02}{at_minute:02}00.wav"
            sf.write(
                wav_filename, audio_segment, audio_info.samplerate, audio_info.subtype
            )
            info(f"  saved extracted wav: {wav_filename} len={len(audio_segment):,}")

        info("  - processing ...")
        audio_segment *= VOLTAGE_MULTIPLIER

        iso_minute = f"{year:04}-{month:02}-{day:02}T{at_hour:02}:{at_minute:02}:00Z"
        self.pypam_support.add_segment(audio_segment, iso_minute)

        if self.save_segment_result:
            milli_psd = self.pypam_support.get_milli_psd(audio_segment, iso_minute)
            # Note: preliminary naming for output, etc.
            basename = (
                f"milli_psd_{year:04}{month:02}{day:02}_{at_hour:02}{at_minute:02}00"
            )
            save_netcdf(milli_psd, f"{self.output_dir}/{basename}.nc")
            if self.gen_csv:
                save_csv(milli_psd, f"{self.output_dir}/{basename}.csv")
