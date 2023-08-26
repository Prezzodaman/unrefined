# v1.1:
#	Replayer:
#		Added support for 16-bit renders (!!!)
#		Fixed safe downsampling in stereo
#		Added more info to the --verbose option
#		Added the option to render each track as its own individual file
#		Changed behaviour of --stereo_finalize
#	Tools:
#		Added a "Gargle" effect
#		Added an oscillator tool
#		Added an additive synthesis tool
#		Added a "Topper" effect

# v1.0.1:
#	Replayer:
#		Tracks now render in order (important for stereo renders)

import pyaudio
import time
import json
import os
import argparse
import wave
import multiprocessing
from prefs import load_prefs

def render(verbose,beat_length,samples,command_arguments_amount,optional_arguments_amount,track_length,quality,current_pattern_track,track_number,track_amount,sixteen_bit,mixed_depth,render_tracks,custom_file_name,render_to_raw,crispy,sample_rate,filtered):
	if render_tracks:
		if custom_file_name=="":
			file_name="track"
		else:
			file_name=custom_file_name
	else:
		file_name="temp/track"
	file_name+="_" + str(track_number)
	if render_tracks:
		if render_to_raw:
			file_name+=".raw"
		else:
			file_name+=".wav"
	else:
		file_name+=".raw"
	with open(file_name,"wb") as file:
		if verbose:
			print("Summing track " + str(track_number) + "...")

		print_delay=0 # visual feedback
		
		file_track=[]
		start_time=time.perf_counter()
		error=False
		beat_previous=1 # so the beat will always be "unique" at the very start
		current_skip=1
		current_sample=0
		current_skip_slow=True
		current_volume=1
		
		sample_position=0
		sample_bit_skip=0
		sample_start=0 # if it's a wav file, this is where the header starts
		sample_offset=0
		sample_skip_delay=0
		sample_delay=0 # starts from a high number and decreases
		sample_encountered=False # prevents a bug where the sample from the last track will play on the first step if there's nothing there
		sample_cut=False
		sample_reverse=False
		sample_size=0
		sample_signed=0

		hex_digits="0123456789abcdef"
		volume_offsets=[2,3,3.5,3.75,3.875,3.9375,3.96875]

		if sixteen_bit:
			last_sample_byte=32767 # avoids a click when nothing's playing on the first line. this will also hold a 16-bit value if using the 16-bit mode - it'll be split up into 2 bytes when appending to the file array
		else:
			last_sample_byte=127
		params=current_pattern_track[0].split(" ")
		for a in range(0,track_length,quality):
			beat=int(a/beat_length)

			if not error:
				if len(params)<command_arguments_amount-optional_arguments_amount:
					error=True
				if beat!=beat_previous:
						
					# 28/12/2022 - one hell of a revelation.
					# moving the string comparisons into beat!=beat_previous saves an exponential amount of time!
					
					# Examples:
					# nut/blank.usf - before: 21.64 seconds, after: 4.08 seconds
					# wufige/wufige.usf - before: 12.54 seconds, after: 2.18 seconds
					# fresh/blank.usf - before: 47.35 seconds, after: 11 seconds
					# rushin/blank.usf - before: 129.82 seconds, after: 24.21 seconds
					# song/song.usf - before: 52.57 seconds, after: 9.33 seconds
					
					# on average, this is a 5.25x increase in speed!!!
					
					params=current_pattern_track[beat].split(" ") # duplicate code, i know...
					
					for param in range(0,len(params)-optional_arguments_amount):
						if params[param].isdigit():
							if len(params[param])<2: # and it isn't one byte long
								params[param]+="0"
								
					if params[0]=="--":
						sample_cut=True
					 
					# check if the values are hex...
					current_sample_check=0
					param_valid_hex=[False]*(command_arguments_amount-optional_arguments_amount)
					for param in range(0,command_arguments_amount-optional_arguments_amount):
						if set(params[param]).issubset(set(hex_digits)):
							param_valid_hex[param]=True
									
					if all(param_valid_hex):
						if params[0]!="--":
							if params[0][0]=="-":
								current_sample_check=abs(int(params[0],16))
							else:
								current_sample_check=int(params[0],16)
					
					if param_valid_hex[1]:
						# check on each unique beat if the sample's playing slowly or not...
						if params[1][0]!="0" or params[1][1]!="0":
							current_skip_slow=params[1][0]=="0"
							if current_skip_slow:
								sample_skip_delay=0
					
						# has a beat been "beaten" and speed command non-zero?
						if params[1][0]!="0" or params[1][1]!="0":
							if current_skip_slow:
								if params[1][1].isdigit():
									current_skip=int(params[1][1],16)+1
							else:
								if params[1][0].isdigit():
									current_skip=int(params[1][0],16)+1

					if len(params)==5:
						if params[4].lower()=="r":
							sample_reverse=True
						
					if param_valid_hex[3]:
						if len(params[3])==2:
							if int(params[3][1],16)!=0:
								current_volume=int(params[3][1],16)+1
							
				if current_sample_check!=0: # is the current sample actually something?
					if mixed_depth:
						header=samples[current_sample-1][0][0] | (samples[current_sample-1][0][1]<<8) | (samples[current_sample-1][0][2]<<16) | (samples[current_sample-1][0][3]<<24) # a 32-bit value containing the first 4 bytes of the file. used to decide whether or not it's a wav file
						if header==1179011410: # "RIFF"
							sample_start=40

					sample_size=0
					sample_bit_skip=1
					sample_cut=False
					if current_sample_check<len(samples)+1: # make sure the sample exists and isn't out of range
						sample_encountered=True
						current_sample=current_sample_check
						if mixed_depth:
							sample_size=len(samples[current_sample-1][0])-1
							if samples[current_sample-1][2]==1: # stereo?
								if samples[current_sample-1][1]==0: # 8 bit?
									sample_bit_skip=2
								if samples[current_sample-1][1]==1: # 16 bit?
									sample_bit_skip=4
							sample_signed=samples[current_sample-1][3]
						else:
							sample_size=len(samples[current_sample-1])-1
						sample_offset=int(params[2],16)*255*sample_bit_skip
						if param_valid_hex[3]:
							current_volume=int(params[3][1],16)+1
							if current_volume>8:
								current_volume=8
					sample_delay_previous=sample_delay-1 # hacky
					if sample_delay_previous<0:
						sample_delay_previous=0
					if beat!=beat_previous:
						sample_delay=(int(params[3][0],16)*127)+1
					if sample_delay==1 and sample_delay_previous==0:
						if sample_reverse: # start the sample from the end
							sample_position=sample_size-1
						else:
							sample_position=sample_offset+sample_start
						if len(params)<=command_arguments_amount-optional_arguments_amount: # no optional command?
							sample_reverse=False
							sample_position=sample_offset+sample_start
						if param_valid_hex[1]:
							if current_skip_slow:
								current_skip=int(params[1][1],16)+1
							else:
								current_skip=int(params[1][0],16)+1
					
				if sample_position<sample_size and sample_position>=sample_start: # play through the entire sample
					current_volume_offset=0
					if current_volume>1:
						if current_volume-2<len(volume_offsets):
							current_volume_offset=32*volume_offsets[current_volume-2]
						else:
							current_volume_offset=32*volume_offsets[-1]
					if sample_cut:
						if sixteen_bit:
							last_sample_byte=32767
						else:
							last_sample_byte=127 # to avoid a click when replaying a sample after a cut
					else:
						if mixed_depth: # song contains a mixture of 8 and 16 bit samples
							sample_position_byte=samples[current_sample-1][0][sample_position]
							if samples[current_sample-1][1]==1: # is this sample 16 bit?
								if sixteen_bit: # if rendering in 16 bit, construct the full value from 2 bytes
									sample_position_byte=samples[current_sample-1][0][sample_position] | (samples[current_sample-1][0][sample_position+1]<<8)
									if sample_signed:
										sample_position_byte=(sample_position_byte+32768) & 65535
								else: # if rendering in 8 bit, keep only the low byte
									sample_position_byte=samples[current_sample-1][0][sample_position+1]
									if sample_signed:
										sample_position_byte=(sample_position_byte+128) & 255
						else:
							sample_position_byte=samples[current_sample-1][sample_position]
							if sample_signed:
								sample_position_byte=(sample_position_byte+128) & 255
						if sixteen_bit:
							if mixed_depth:
								if samples[current_sample-1][1]==0: # if rendering in 16 bit, and the current sample is 8 bit, make this sample "16 bit"
									sample_position_byte*=255
							else: # if all samples are 8 bit, and we're rendering in 16 bit, make all samples "16 bit"
								sample_position_byte*=255
							last_sample_byte=int((sample_position_byte>>(current_volume-1))+(current_volume_offset*255)) # the exciting variable that actually contains the sample byte we need!
						else:
							last_sample_byte=int((sample_position_byte>>(current_volume-1))+current_volume_offset)
						if last_sample_byte<0: # to avoid clipping
							last_sample_byte=0
						if sixteen_bit:
							if last_sample_byte>65535:
								last_sample_byte=65535
						else:
							if last_sample_byte>255:
								last_sample_byte=255
					if sixteen_bit:
						file_track.append(last_sample_byte & 255)
						file_track.append(last_sample_byte>>8)
						if crispy:
							file_track.append(last_sample_byte & 255)
							file_track.append(last_sample_byte>>8)
					else:
						file_track.append(last_sample_byte)
						if crispy:
							file_track.append(last_sample_byte)
					if sample_encountered: # move the sample forward or back depending on speed and whether it's reversing or not
						if not sample_cut:
							if current_skip_slow and current_skip!=1:
								sample_skip_delay+=quality*sample_bit_skip
								if sample_skip_delay>(current_skip*quality*sample_bit_skip)-1:
									sample_skip_delay=0
									if sample_reverse:
										sample_position-=quality*sample_bit_skip
									else:
										sample_position+=quality*sample_bit_skip
							else:
								if sample_reverse:
									sample_position-=current_skip*quality*sample_bit_skip
								else:
									sample_position+=current_skip*quality*sample_bit_skip
				else: # when the sample's ended, add nothing
					if sixteen_bit:
						file_track.append(last_sample_byte & 255)
						file_track.append(last_sample_byte>>8)
						if crispy:
							file_track.append(last_sample_byte & 255)
							file_track.append(last_sample_byte>>8)
					else:
						file_track.append(last_sample_byte)
						if crispy:
							file_track.append(last_sample_byte)
				if sample_delay>0:
					sample_delay-=1
				beat_previous=beat
		end_time=time.perf_counter()
		if filtered and sixteen_bit:
			for a in range(0,len(file_track)-4,2):
				byte_filtered=((file_track[a] | (file_track[a+1]<<8))+(file_track[a+2] | (file_track[a+3]<<8)))//2
				file_track[a]=byte_filtered & 255
				file_track[a+1]=byte_filtered>>8
		if render_tracks:
			if render_to_raw:
				file.write(bytearray(file_track))
			else:
				file_open=False
				try:
					wave_file=wave.open(file_name,"w")
				except:
					print("Error: this file is currently being accessed elsewhere!")
					file_open=True
				if not file_open:
					wave_file.setnchannels(1)
					if sixteen_bit:
						wave_file.setsampwidth(2)
					else:
						wave_file.setsampwidth(1)
					wave_file.setframerate(sample_rate//quality)
					wave_file.writeframesraw(bytearray(file_track))
					wave_file.close()
		else:
			file.write(bytearray(file_track))
		file_track.clear()
	if verbose:
		print("Track " + str(track_number) + " summed in " + str(round(end_time-start_time,3)) + " seconds!")

if __name__ == "__main__":
	parser=argparse.ArgumentParser(description="Plays back a .usf file")
	parser.add_argument("file", type=argparse.FileType("r"),help="The name of the file to play back")
	parser.add_argument("-v", "--verbose", action="store_true", help="Shows details about the file as it's being rendered, such as the length, samples and tracks.")
	parser.add_argument("-q", "--quality", type=int,help="Renders the module in lower quality for quick playback, rendering every nth byte of each sample. Uses highest quality (0) by default.",default=0)
	parser.add_argument("-c", "--crispy", action="store_true", help="Makes the rendered file sound Nice 'n' Crispy by repeating every byte twice. Recommended for files with a low sample rate.")
	parser.add_argument("-r", "--raw", action="store_true", help="Renders the file to a .raw file instead of a .wav.")
	parser.add_argument("-f", "--file_name", type=str, help="Specify a custom filename for the rendered file (without extension).",default="")
	parser.add_argument("-np", "--no_play", action="store_true", help="Renders the file without playing it back.")
	parser.add_argument("-s", "--stereo", action="store_true", help="Puts every odd track in the left channel, and every even track in the right channel.")
	parser.add_argument("-sf", "--stereo_finalize", action="store_true", help="\"Finalize\" a stereo render by keeping all bass in the centre channel and reducing the stereo width. Because of the extra steps required, this significantly increases the render time.")
	parser.add_argument("-sd", "--safe_downsample", action="store_true", help="Performs a \"safe downsample\" on the rendered file, adding a low-pass filter before downsampling to reduce the amount of aliasing. Recommended if the sample rate of the file is above 64000 Hz, as it only uses half the space while retaining near identical sound quality.")
	parser.add_argument("-d", "--ding", action="store_true", help="Plays a \"ding\" sound to let you know when it's finished rendering. Only effective if -np is used.")
	parser.add_argument("-sb", "--sixteen_bit", action="store_true", help="Renders the file in 16-bit. The result has notably less noise, but it takes longer to render.")
	parser.add_argument("-t", "--tracks", action="store_true", help="Renders each track as its own file. Custom filenames defined using -f will also work!")
	args=parser.parse_args()

	file_name=args.file.name
	quality=args.quality+1
	verbose=args.verbose
	crispy=args.crispy
	render_to_raw=args.raw
	no_play=args.no_play
	stereo=args.stereo
	safe_downsample=args.safe_downsample
	stereo_finalize=args.stereo_finalize
	ding=args.ding
	sixteen_bit=args.sixteen_bit
	render_tracks=args.tracks
	custom_file_name=args.file_name
	
	# prefs defaults...
	stutter=1
  
	# actual if applicable...
	prefs=load_prefs("prefs.cfg")
	if "buffer_size" in prefs:
		if isinstance(prefs["buffer_size"],int):
			stutter=prefs["buffer_size"]
	
	samples=[]
	json_success=True
	command_arguments_amount=5
	optional_arguments_amount=1
	blank_command=""
	for a in range(0,command_arguments_amount-optional_arguments_amount): # -1 because reverse
		blank_command+="00 "
	blank_command=blank_command[:-1]

	print("Unrefined Replayer v1.1.0")
	print("by Presley Peters, 2022-2023")
	print()
	if quality==1:
		print("Rendering file...")
	else:
		print("Rendering file at 1/" + str(quality) + " quality...")
	if verbose:
		print()

	with open(file_name,"r") as file:
		try:
			song_file=json.load(file)
		except Exception as e:
			print("Error loading file! \n" + str(e))
			json_success=False

	if json_success:
		keys_exist=True
		if not "samples" in song_file:
			keys_exist=False
			print("Error: Sample list doesn't exist!")
		elif not "patterns" in song_file:
			keys_exist=False
			print("Error: Pattern list doesn't exist!")
		elif not "arrangement" in song_file:
			keys_exist=False
			print("Error: Arrangement list doesn't exist!")
		elif not "sample_rate" in song_file:
			keys_exist=False
			print("Error: Sample rate not specified!")
		elif not "beat_length" in song_file:
			keys_exist=False
			print("Error: Beat length not specified!")
		elif not os.path.exists(os.path.dirname(os.path.abspath(custom_file_name))):
			keys_exist=False # reusing variable names sssh dont tell anyone
			print("Error: Path \"" + os.path.dirname(os.path.abspath(custom_file_name)) + "\" doesn't exist!")
		elif stutter<1:
			keys_exist=False
			print("Error: Frames per chunk ^ 2 cannot be below 1!")
		elif stutter>64:
			keys_exist=False
			print("Error: Frames per chunk ^ 2 cannot be above 64!")
		elif stereo_finalize and not stereo:
			keys_exist=False
			print("Error: Stereo finalize can only be used alongside the stereo option!")

		if keys_exist:
			sample_rate=song_file["sample_rate"]
			beat_length=song_file["beat_length"] # in samples
			#loops=song_file["loops"]
			
			if sample_rate*2>44100 and crispy:
					print("Warning: Crisping will have little effect, as the sample rate (" + str(sample_rate*2) + " Hz) has a bandwidth beyond the percievable range!")
			elif sample_rate>44100 and not safe_downsample:
				print("Warning: The sample rate (" + str(sample_rate) + " Hz) has a bandwidth beyond the percievable range!")
			elif stereo and render_tracks:
				print("Warning: The stereo option has no effect when rendering individual tracks!")
					
			mixed_depth=False # if the song contains both 8 and 16 bit samples

			sample_names=song_file["samples"]
			sample_names_exist=True
			for name in sample_names:
				sample_depth=0 # 0 = 8 bit, 1 = 16 bit
				sample_stereo=0
				sample_signed=0
				if isinstance(name,list): # backwards compatibility...
					mixed_depth=True
					sample_name=name[0]
					if len(name)>1:
						if isinstance(name[1],int):
							sample_depth=name[1]==1
						if len(name)>2:
							if isinstance(name[2],int):
								sample_stereo=name[2]==1
							if len(name)>3:
								if isinstance(name[3],int):
									sample_signed=name[3]==1
				else:
					sample_name=name
					mixed_depth=False

				sample_name_full=os.path.dirname(os.path.abspath(file_name))+"/"+sample_name
				if os.path.exists(sample_name_full):
					if verbose:
						print("Loading sample " + sample_name + "...")
					with open(sample_name_full, "rb") as file:
						if mixed_depth:
							samples.append([file.read(),sample_depth,sample_stereo,sample_signed])
						else:
							samples.append(file.read())
					
				else:
					print("Error: File \"" + sample_name + "\" doesn't exist!")
					sample_names_exist=False

			if verbose:
				print()

			if sample_names_exist:

				pattern_tracks=0
				pattern_track_length=0

				for pattern_name in song_file["arrangement"]:
					pattern_found=False
					for pattern in song_file["patterns"]:
						if pattern_name==pattern["name"]:
							pattern_found=True
					if not pattern_found:
						print()
						print("Error: Pattern \"" + pattern_name + "\" doesn't exist!")

				if pattern_found:

					# ParePare the pattern, filling in the blanks (tracks)
					# Basically compiling all the arrangement patterns into one big one, because it's more convenient

					# Find highest amount of tracks, and length of longest track
					pattern_track_lengths=[]
					for pattern in song_file["patterns"]:
						pattern_track_length=0
						if len(pattern["pattern"])>pattern_tracks:
							pattern_tracks=len(pattern["pattern"])
						for track in pattern["pattern"]:
							if len(track)>pattern_track_length:
								pattern_track_length=len(track)
						pattern_track_lengths.append(pattern_track_length)

					# Fill in the blank tracks
					patterns_updated=[]
					for counter,pattern in enumerate(song_file["patterns"]):
						if len(pattern["pattern"])==pattern_tracks:
							patterns_updated.append(pattern["pattern"])
						else: # not enough tracks!
							track_blank=[]
							for a in range(0,pattern_track_lengths[counter]):
								track_blank.append(blank_command)
								
							pattern_temp=pattern["pattern"]
							# append the blank track to stand in for all missing tracks
							for a in range(len(pattern["pattern"])-1,pattern_tracks):
								pattern_temp.append(track_blank)

							patterns_updated.append(pattern_temp)

					# Extend any shorter tracks
					for pattern_num in range(0,len(patterns_updated)):
						for track_num in range(0,len(patterns_updated[pattern_num])):
							if len(patterns_updated[pattern_num][track_num])<pattern_track_lengths[pattern_num]:
								for a in range(len(patterns_updated[pattern_num][track_num]),pattern_track_lengths[pattern_num]):
									patterns_updated[pattern_num][track_num].append(blank_command)
									
					# Combine all patterns into one big one!
					pattern=[]
					for track_num in range(0,pattern_tracks): # Track at a time baby
						pattern_track_temp=[]
						for pattern_name in song_file["arrangement"]: # go through arrangement and find appropriate pattern...
							for pattern_temp in song_file["patterns"]: # go through patterns until the correct one is found
								if pattern_temp["name"]==pattern_name: # found correct pattern?
									pattern_track_temp+=pattern_temp["pattern"][track_num]
						pattern.append(pattern_track_temp)

					pattern_length=len(pattern[0]) # is assumed the same for all other tracks!
					pattern_tracks=len(pattern)
					track_length=beat_length*pattern_length # in samples

					if sample_rate//quality<2000:
						print("Error: Sample rate too low! Try using a lower quality value.")
					else:
						if len(sample_names)==0 and pattern_length==1:
							print("Error: This file is empty!")
						else:
							if verbose:
								print("File: " + file_name)
								print("Tracks: " + str(pattern_tracks))
								print("Song length: " + str(pattern_length//4) + " beats")
								print("Samples:")
								for counter,name in enumerate(sample_names):
									if mixed_depth:
										depth="8"
										if name[1]==1:
											depth="16"
										print("    Sample " + str(counter+1) + ": " + name[0] + ", Bit depth: " + depth + ", Size: " + str(len(samples[counter][0])/1000) + " KB")
									else:
										print("    Sample " + str(counter+1) + ": " + name + ", Size: " + str(len(samples[counter])/1000) + " KB")
								sample_ram_usage=0
								for sample in samples:
									if mixed_depth:
										sample_ram_usage+=len(sample[0])
									else:
										sample_ram_usage+=len(sample)
								print("Sample RAM usage: " + str(round(sample_ram_usage/1000,3)) + " KB")
								print()

								#print("Loops added: " + str(loops))
								print("Beat length in samples: " + str(beat_length))
								print("Sample rate: " + str(sample_rate) + " Hz")
								if quality>1:
									print("    Reduced: " + str(sample_rate//quality) + " Hz")
								if crispy:
									print("    Crispy: " + str((sample_rate*2)//quality) + " Hz")
								if safe_downsample:
									print("    Downsampled: " + str((sample_rate//quality)//2) + " Hz")
								try:
									beats_per_minute=int(60000/((((track_length/sample_rate)*1000/1)/(pattern_length//16))/4)*1000)/1000
								except:
									beats_per_minute="N/A"
								print("Beats per minute: " + str(beats_per_minute))
								length_seconds=track_length/sample_rate
								if length_seconds<60:
									print("Length: " + str(round(length_seconds)) + " seconds")
								else:
									print("Length: " + str(round(length_seconds/60)) + " minutes, " + str(round((length_seconds%1)*60)) + " seconds")
								print()
									
								print("Patterns:")
								pattern_names=[]
								pattern_lengths=[] # easier to manage ;)
								pattern_info_str=[]
								for a in song_file["patterns"]:
									pattern_names.append(a["name"])
									pattern_length_temp=0
									for track in a["pattern"]:
										if len(track)>pattern_length_temp:
											pattern_length_temp=len(track)
									pattern_lengths.append(pattern_length_temp)
									pattern_info_str.append(a["name"] + " (length: " + str(pattern_length_temp) + ")")
								print("    "+", ".join(pattern_info_str))
								print()

								print("Arrangement:")
								arrangement=[]
								for a in song_file["arrangement"]:
									arrangement.append(a)
								print("    "+", ".join(arrangement) + " (" + str(len(song_file["arrangement"])) + " patterns)")
								print()
							
							start_time=time.perf_counter()

							track_number=1 # for visual feedback only!
							error=False # very vague name, I know
							
							if crispy:
								sample_rate*=2
							 
							if not os.path.isdir("temp") and not render_tracks:
								os.mkdir("temp")

							manager=multiprocessing.Manager()
							processes=[]
							for track in range(0,pattern_tracks):
								# assemble the current track into an array from which to read...
								current_pattern_track=[]
								for beat in range(0,pattern_length):
									if beat<len(pattern[track]):
										current_pattern_track.append(pattern[track][beat])
									else:
										current_pattern_track.append(blank_command)
								processes.append(multiprocessing.Process(target=render,args=(verbose,beat_length,samples,command_arguments_amount,optional_arguments_amount,track_length,quality,current_pattern_track,track+1,pattern_tracks,sixteen_bit,mixed_depth,render_tracks,custom_file_name,render_to_raw,crispy,sample_rate,stereo_finalize,)))
							
							for process in processes:
								process.start()
							for process in processes:
								process.join()

							file_open=False

							# summing time!

							if error:
								print("Error: Incorrect number of line arguments! At least " + str(command_arguments_amount-optional_arguments_amount) + " are required")
							else:
								if not render_tracks: # if rendering individual tracks, skip summing
									track_length_rendered=track_length//quality
									if crispy:
										track_length_rendered*=2
									if stereo:
										file_finished=[0]*track_length_rendered*2
									else:
										file_finished=[0]*track_length_rendered
									print_counter_max=80000 # this will vary depending on the speed of operations
									print_counter=print_counter_max

									position_overall=0
									for track in range(0,pattern_tracks): # go through each track, step through each byte and add it to the file arrays
										track_file_name="temp/track_" + str(track+1) + ".raw"
										with open(track_file_name,"rb") as file:
											position=0
											position_actual=0
											byte=file.read(1)
											while byte:
												if verbose:
													if print_counter>print_counter_max/2:
														percentage=(position_overall/(track_length//quality))/pattern_tracks
														if crispy:
															percentage/=2
														percentage*=100
														print("Summing all tracks together... (" + str(track+1) + "/" + str(pattern_tracks) + ") " + str(round(percentage,3)) + "%    ",end="\r")
														print_counter=0
													print_counter+=1

												if position<len(file_finished):
													position_actual=position
													byte_value=int.from_bytes(byte)
													if sixteen_bit:
														byte_value=byte_value | (int.from_bytes(file.read(1))<<8)
												else:
													if sixteen_bit:
														byte_value=32767
													else:
														byte_value=127
												if stereo:
													if track%2==0:
														file_finished[position_actual*2]+=byte_value
													else:
														file_finished[position_actual*2+1]+=byte_value
												else:
													file_finished[position_actual]+=byte_value
												byte=file.read(1)
												position+=1
												position_overall+=1
										os.remove(track_file_name)

									if verbose:
										print("Summing all tracks together... 100%            ",end="\r")
										print()
									
									if stereo:
										for a in range(0,len(file_finished),2):
											if pattern_tracks%2==1: # odd number of tracks?
												if sixteen_bit:
													file_finished[a]-=32767
												else:
													file_finished[a]-=127
											file_finished[a]//=pattern_tracks//2
											file_finished[a+1]//=pattern_tracks//2
											if file_finished[a]<0: # without these checks, the wave will "wrap around" when it clips
												file_finished[a]=0
											if file_finished[a]>65535:
												file_finished[a]=65535
											if file_finished[a+1]<0:
												file_finished[a+1]=0
											if file_finished[a+1]>65535:
												file_finished[a+1]=65535
									else:
										for counter,byte in enumerate(file_finished):
											file_finished[counter]=byte//pattern_tracks
									
									file_finalized=[]
									print_counter=print_counter_max*2
									if stereo_finalize:
										file_finished_orig=file_finished.copy()
										passes=40
										for a in range(0,passes): # we want it to be nice and steep
											file_filtered=[]
											if sixteen_bit:
												previous_byte=32767
											else:
												previous_byte=127
											for b in range(0,len(file_finished),2): # if stereo, file_finished will contain both left and right (interleaved), so we need to sum them together when filtering
												byte=(file_finished_orig[b]+file_finished_orig[b+1])//2
												filtered_byte=(byte+previous_byte)//2
												file_filtered.append(filtered_byte)
												file_filtered.append(filtered_byte)
												previous_byte=byte
												if verbose:
													if print_counter>print_counter_max*2:
														print("Filtering... (" + str(a+1) + "/" + str(passes) + ") " + str(round(((b+(a*len(file_finished_orig)))/(len(file_finished_orig)*passes))*100,3)) + "%       ",end="\r")
														print_counter=0
													else:
														print_counter+=1
											file_finished_orig=file_filtered.copy()
										file_finished_orig.clear()
										if verbose:
											print("Filtering... 100%                ",end="\r")
											print()
											
										print_counter=print_counter_max*2
										for a in range(0,len(file_finished),2):
											if verbose:
												if print_counter>print_counter_max*2:
													print("Finalizing... " + str(round((a/len(file_finished))*100,3)) + "%    ",end="\r")
													print_counter=0
												else:
													print_counter+=1
											sample_sum=(file_finished[a]+file_finished[a+1])//2
											sample_sum_left=(file_finished[a]+sample_sum+file_filtered[a])//3
											sample_sum_right=(file_finished[a+1]+sample_sum+file_filtered[a])//3
											file_finalized.append(sample_sum_left)
											file_finalized.append(sample_sum_right)
										
										file_finished=file_finalized.copy()
										file_finalized.clear()
										if verbose:
											print("Finalizing... 100%      ",end="\r")
											print()
									if safe_downsample and not stereo_finalize: # ignored if finalizing...
										if sixteen_bit:
											previous_byte=32767
										else:
											previous_byte=127
										file_filtered=[]
										file_downsampled=[]
										print_counter=print_counter_max*2
										position=0
										if stereo:
											for byte in range(0,len(file_finished)-2,2):
												if verbose:
													if print_counter>print_counter_max:
														print("Filtering... " + str(round((position/len(file_finished))*100,3)) + "%    ",end="\r")
														print_counter=0
													else:
														print_counter+=1
												file_filtered.append((previous_byte+file_finished[byte])//2)
												if sixteen_bit:
													previous_byte=32767
												else:
													previous_byte=127
												file_filtered.append((previous_byte+file_finished[byte+1])//2)
												position+=2
										else:
											for byte in file_finished: # note to future me: one pass is enough to completely eliminate aliasing!
												if verbose:
													if print_counter>print_counter_max:
														print("Filtering... " + str(round((position/len(file_finished))*100,3)) + "%    ",end="\r")
														print_counter=0
													else:
														print_counter+=1
												file_filtered.append((byte+previous_byte)//2) # that my friends is a low-pass filter. (mind explodes)
												previous_byte=byte
												position+=1
												
										if verbose:
											print("Filtering... 100%          ",end="\r")
											print()
										print_counter=print_counter_max

										# now we "downsample" the filtered file... by skipping every other byte :p
										position=0
										while position<len(file_filtered):
											if verbose:
												if print_counter>print_counter_max:
													print("Downsampling... " + str(round((position/len(file_filtered))*100,2)) + "%    ",end="\r")
													print_counter=0
												else:
													print_counter+=1
											if stereo:
												file_downsampled.append(file_filtered[position])
												file_downsampled.append(file_filtered[position+1])
												position+=4
											else:
												file_downsampled.append(file_filtered[position])
												position+=2
										file_finished=file_downsampled.copy()
										file_filtered.clear()
										file_downsampled.clear()

										if verbose:
											print("Downsampling... 100%            ",end="\r")
											print()
											print()

								end_time=time.perf_counter()
								time_taken=end_time-start_time
								if render_tracks:
									tracks_or_file="Tracks"
								else:
									tracks_or_file="File"
								if time_taken<60:
									print(tracks_or_file + " rendered in " + str(round(time_taken,2)) + " seconds!")
								else:
									print(tracks_or_file + " rendered in " + str(round(time_taken/60)) + " minutes, " + str(round((time_taken%1)*60)) + " seconds!")

							if verbose and not render_tracks:
								file_size=len(file_finished)
								if sixteen_bit:
									file_size*=2
								print("File size: " + str(round(file_size/1000,3)) + " KB")

							if not render_tracks:
								if custom_file_name=="":
									file_name="result"
								else:
									file_name=custom_file_name

								file_open=False
								if sixteen_bit:
									for a in range(0,len(file_finished)): # convert to signed
										file_finished[a]=(file_finished[a]+32768) & 65535
								if render_to_raw:
									file_name+=".raw"
									with open(file_name, "wb") as file:
										file.write(bytearray(file_finished))
								else:
									file_name+=".wav"
									try:
										wave_file=wave.open(file_name,"w")
									except:
										print("Error: this file is currently being accessed elsewhere!")
										file_open=True
										
								if not file_open:
									if sixteen_bit:
										file_sixteen_bit=[]
										for byte in file_finished:
											file_sixteen_bit.append(byte & 255)
											file_sixteen_bit.append(byte>>8)
										file_finished=file_sixteen_bit.copy()
										file_sixteen_bit.clear()
									if render_to_raw:
										with open(file_name, "wb") as file:
											file.write(bytearray(file_finished))
									else:
										if stereo:
											wave_file.setnchannels(2)
										else:
											wave_file.setnchannels(1)
										if sixteen_bit:
											wave_file.setsampwidth(2) # in bytes (1 is 8 bit, 2 is 16 bit, etc.)
										else:
											wave_file.setsampwidth(1)
										if safe_downsample:
											wave_file.setframerate((sample_rate//quality)//2)
										else:
											wave_file.setframerate(sample_rate//quality)
										wave_file.writeframesraw(bytearray(file_finished))
										wave_file.close()

								if (no_play and ding) or (not no_play):
									pya=pyaudio.PyAudio()
								if no_play or render_tracks:
									if ding:
										print("Done!")
										stream=pya.open(format=pyaudio.paUInt8,rate=11025,output=True,channels=1,frames_per_buffer=2**stutter)
										try:
											with open("ding.raw","rb") as file:
												for byte in file:
													stream.write(byte)
										except:
											pass # do nothing if the file doesn't exist
								else:
									print()
									print("Playing...")
									play_sample_rate=sample_rate//quality
									if safe_downsample:
										play_sample_rate=play_sample_rate//2
									play_channels=1
									if stereo:
										play_channels=2
									
									if sixteen_bit:
										stream=pya.open(format=pyaudio.paInt16,rate=play_sample_rate,output=True,channels=play_channels,frames_per_buffer=2**stutter)
									else:
										stream=pya.open(format=pyaudio.paUInt8,rate=play_sample_rate,output=True,channels=play_channels,frames_per_buffer=2**stutter)
									
									with open(file_name,"rb") as file:
										for byte in file: # the only occasion we'll need to read from the file instead
											stream.write(byte)
											
								if not no_play:
									stream.stop_stream()
									stream.close()
									pya.terminate()
							if not ding:
								print("Done!")

							#if loops>0:
							#    for a in range(0,loops):
							#        with open("result.raw", "ab") as file:
							#            file.write(bytearray(file_finished))
