import pyaudio
import time
import json
import os
import argparse
import wave
import multiprocessing
from prefs import load_prefs

def render(verbose,beat_length,samples,command_arguments_amount,optional_arguments_amount,track_length,quality,current_pattern_track,file_tracks,track_number,track_amount):
    if verbose:
        print("Summing track " + str(track_number) + "...")

    print_delay=0 # visual feedback
    
    start_time=time.perf_counter()
    error=False
    file_track=[]
    sample_position=0
    beat_previous=1 # so the beat will always be "unique" at the very start
    current_skip=1
    current_sample=0
    current_skip_slow=True
    current_volume=1
    sample_offset=0
    sample_skip_delay=0
    sample_delay=0 # starts from a high number and decreases
    sample_encountered=False # prevents a bug where the sample from the last track will play on the first step if there's nothing there
    last_sample_byte=127
    volume_offsets=[2,3,3.5,3.75,3.875,3.9375,3.96875]
    sample_cut=False
    sample_reverse=False
    sample_size=0
    hex_digits="0123456789abcdef"
    last_sample_byte=127 # to avoid a click when nothing's playing on the first line
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
                sample_size=0
                sample_cut=False
                if current_sample_check<len(samples)+1: # make sure the sample exists and isn't out of range
                    sample_encountered=True
                    current_sample=current_sample_check
                    sample_size=len(samples[current_sample-1])-1
                    sample_offset=int(params[2],16)*255
                    if param_valid_hex[3]:
                        current_volume=int(params[3][1],16)+1
                        if current_volume>8: # because the samples are (SHOULD BE... you pesky user) 8 bit and we don't want any errors!
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
                        sample_position=sample_offset
                    if len(params)<=command_arguments_amount-optional_arguments_amount: # no optional command?
                        sample_reverse=False
                        sample_position=sample_offset
                    if param_valid_hex[1]:
                        if current_skip_slow:
                            current_skip=int(params[1][1],16)+1
                        else:
                            current_skip=int(params[1][0],16)+1
                
            if sample_position<sample_size and sample_position>=0: # play through the entire sample
                current_volume_offset=0
                if current_volume>1:
                    if current_volume-2<len(volume_offsets):
                        current_volume_offset=32*volume_offsets[current_volume-2]
                    else:
                        current_volume_offset=32*volume_offsets[-1]
                if sample_cut:
                    last_sample_byte=127 # to avoid a click when replaying a sample after a cut
                else:
                    last_sample_byte=int((samples[current_sample-1][sample_position]>>(current_volume-1))+current_volume_offset) # the exciting variable that actually contains the sample byte we need!
                    if last_sample_byte<0: # to avoid clipping
                        last_sample_byte=0
                    elif last_sample_byte>255:
                        last_sample_byte=255
                file_track.append(last_sample_byte)
                if sample_encountered: # move the sample forward or back depending on speed and whether it's reversing or not
                    if not sample_cut:
                        if current_skip_slow and current_skip!=1:
                            sample_skip_delay+=quality
                            if sample_skip_delay>(current_skip*quality)-1:
                                sample_skip_delay=0
                                if sample_reverse:
                                    sample_position-=quality
                                else:
                                    sample_position+=quality
                        else:
                            if sample_reverse:
                                sample_position-=current_skip*quality
                            else:
                                sample_position+=current_skip*quality
            else: # when the sample's ended, add nothing
                file_track.append(last_sample_byte) # we use last_sample_byte instead of 127 so there's less clicking!
            if sample_delay>0:
                sample_delay-=1
            beat_previous=beat
    end_time=time.perf_counter()
    if verbose:
        print("Track " + str(track_number) + " summed in " + str(round(end_time-start_time,2)) + " seconds!")
    file_tracks.append([track_number-1,file_track])

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description="Plays back a .usf file")
    parser.add_argument("file", type=argparse.FileType("r"),help="The name of the file to play back")
    parser.add_argument("-v", "--verbose", action="store_true", help="Shows details about the module as it's being rendered")
    parser.add_argument("-q", "--quality", type=int,help="Renders the module in lower quality for quick playback, rendering every nth byte. Uses highest quality (0) by default",default=0)
    parser.add_argument("-c", "--crispy", action="store_true", help="Makes the rendered file sound Nice 'n' Crispy by repeating every byte twice")
    parser.add_argument("-r", "--raw", action="store_true", help="Renders the file to a .raw file instead of a .wav")
    parser.add_argument("-f", "--file_name", type=str, help="Specify a custom filename for the rendered file (without extension)",default="")
    parser.add_argument("-np", "--no_play", action="store_true", help="Renders the file without playing it back")
    parser.add_argument("-s", "--stereo", action="store_true", help="Puts every odd track in the left channel, and every even track in the right channel (not currently supported alongside the -sd option)")
    parser.add_argument("-sf", "--stereo_finalize", action="store_true", help="\"Finalize\" a stereo render by reducing stereo width, and keeping all bass in the centre channel")
    parser.add_argument("-sd", "--safe_downsample", action="store_true", help="Performs a \"safe downsample\" on the rendered file, adding a low-pass filter before downsampling to reduce the amount of aliasing. This is absolutely essential if you're using a sample rate above 64000 Hz, as it only uses half the space while retaining near identical sound quality.")
    parser.add_argument("-d", "--ding", action="store_true", help="Plays a \"ding\" sound to let you know when it's finished rendering. Only effective if -np is used.")
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

    print("Unrefined Replayer v1.0.0 alpha")
    print("by Presley Peters, 2022")
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
        elif not os.path.exists(os.path.dirname(os.path.abspath(args.file_name))):
            keys_exist=False # reusing variable names sssh dont tell anyone
            print("Error: Path \"" + os.path.dirname(os.path.abspath(args.file_name)) + "\" doesn't exist!")
        elif safe_downsample and stereo:
            print("Warning: Safe downsample in stereo isn't fully supported yet!")
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
            
            if crispy and sample_rate*2>48000:
                print("Warning: Crisping will have little effect, as the sample rate (" + str(sample_rate*2) + " Hz) is beyond the percievable range!")
                    
            sample_names=song_file["samples"]

            sample_names_exist=True
            for name in sample_names:
                sample_name=os.path.dirname(os.path.abspath(file_name))+"/"+name
                if os.path.exists(sample_name):
                    if verbose:
                        print("Loading sample " + name + "...")
                    with open(sample_name, "rb") as file:
                        samples.append(file.read())
                    
                else:
                    print("Error: File \"" + sample_name + "\" doesn't exist!")
                    sample_names_exist=False

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
                        if verbose:
                            print()
                            print("File: " + file_name)
                            print("Tracks: " + str(pattern_tracks))
                            print("Song length: " + str(pattern_length//4) + " beats")
                            print("Samples:")
                            for counter,name in enumerate(sample_names):
                                print("    Sample " + str(counter+1) + ": " + name + ", Size: " + str(len(samples[counter])/1000) + " KB")
                            sample_ram_usage=0
                            for sample in samples:
                                sample_ram_usage+=len(sample)
                            print("Sample RAM usage: " + str(sample_ram_usage/1000) + " KB")
                                
                            print("Patterns:")
                            pattern_names=[]
                            for a in song_file["patterns"]:
                                pattern_names.append(a["name"])
                            print("    "+", ".join(pattern_names))
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
                            print("Length: " + str(round(track_length/sample_rate,2)) + " seconds")
                            print()
                        
                        start_time=time.perf_counter()

                        track_number=1 # for visual feedback only!
                        error=False # very vague name, I know
                        
                        if crispy:
                            sample_rate*=2
                         
                        manager=multiprocessing.Manager()
                        manager_list=manager.list()
                        processes=[]
                        for track in range(0,len(pattern)):
                            # assemble the current track into an array from which to read...
                            current_pattern_track=[]
                            for beat in range(0,pattern_length):
                                if beat<len(pattern[track]):
                                    current_pattern_track.append(pattern[track][beat])
                                else:
                                    current_pattern_track.append(blank_command)
                            
                            processes.append(multiprocessing.Process(target=render,args=(verbose,beat_length,samples,command_arguments_amount,optional_arguments_amount,track_length,quality,current_pattern_track,manager_list,track+1,len(pattern),)))
                        
                        for process in processes:
                            process.start()
                        for process in processes:
                            process.join()
                            
                        file_tracks_temp=list(manager_list).copy()
                        
                        # assemble the tracks in order...
                        file_tracks=[None]*len(pattern)
                        # format: [0,[track data]],[1,[track data]]
                        for index in file_tracks_temp:
                            file_tracks[index[0]]=index[1]

                        # summing time!

                        if error:
                            print("Error: Incorrect number of line arguments! At least " + str(command_arguments_amount-optional_arguments_amount) + " are required")
                        else:
                            
                            file_finished=[]
                            file_finished_left=[]
                            file_finished_right=[]
                            print_counter_max=80000 # this will vary depending on the speed of operations
                            print_counter=print_counter_max
                            for position in range(0,track_length//quality):
                                if verbose:
                                    if print_counter==print_counter_max:
                                        print("Summing all tracks together... " + str(round((position/(track_length//quality))*100,2)) + "%    ",end="\r")
                                        print_counter=0
                                    print_counter+=1
                                sample_sum=0
                                sample_sum_left=0
                                sample_sum_right=0
                                track_counter=0
                                for counter,track in enumerate(file_tracks):
                                    if position<len(track):
                                        sample_sum+=track[position]
                                        if counter%2==0:
                                            sample_sum_left+=track[position]
                                        else:
                                            sample_sum_right+=track[position]
                                            
                                sample_sum=sample_sum//pattern_tracks
                                if pattern_tracks>1:
                                    if len(pattern)%2==1:
                                        sample_sum_left-=127
                                    sample_sum_left=sample_sum_left//(pattern_tracks//2)
                                    if sample_sum_left<0: # for some reason, some minor clipping happens - but it's only minor (like, by a few bytes) so I'll leave this for now. not that important an issue, I think!
                                        sample_sum_left=1
                                    if sample_sum_left>255:
                                        sample_sum_left=255
                                    sample_sum_right=sample_sum_right//(pattern_tracks//2)
                                if stereo:
                                    file_finished_left.append(sample_sum_left)
                                    file_finished_right.append(sample_sum_right)
                                    if stereo_finalize:
                                        file_finished.append(sample_sum)
                                    else:
                                        file_finished.append(sample_sum_left)
                                        file_finished.append(sample_sum_right)
                                        if crispy:
                                            file_finished.append(sample_sum_left)
                                            file_finished.append(sample_sum_right)
                                else:
                                    file_finished.append(sample_sum)
                                    if crispy:
                                        file_finished.append(sample_sum)

                            if verbose:
                                print("Summing all tracks together... 100.0%     ",end="\r")
                                print()
                                
                            file_finalized=[]
                            print_counter=print_counter_max*2
                            if stereo_finalize: # file_finished will contain just the mono if finalizing
                                file_finished_orig=file_finished.copy()
                                passes=40
                                for a in range(0,passes): # we want it to be nice and steep
                                    file_filtered=[]
                                    previous_byte=127
                                    for position,byte in enumerate(file_finished_orig):
                                        filtered_byte=(byte+previous_byte)//2
                                        file_filtered.append(filtered_byte)
                                        previous_byte=byte
                                        if verbose:
                                            if print_counter==print_counter_max*4:
                                                print("Filtering... " + str(round(((position+(a*len(file_finished_orig)))/(len(file_finished_orig)*passes))*100,2)) + "%    ",end="\r")
                                                print_counter=0
                                            else:
                                                print_counter+=1
                                    file_finished_orig=file_filtered.copy()
                                if verbose:
                                    print("Filtering... 100.0%    ",end="\r")
                                    print()
                                    
                                print_counter=print_counter_max*2
                                for position,(byte_left,byte_right,byte_both,byte_filtered) in enumerate(zip(file_finished_left,file_finished_right,file_finished,file_filtered)):
                                    if verbose:
                                        if print_counter==print_counter_max*4:
                                            print("Finalizing... " + str(round((position/len(file_finished))*100,2)) + "%    ",end="\r")
                                            print_counter=0
                                        else:
                                            print_counter+=1
                                    # the following bit worked first try BOOYAKA BOOYAKA!!!!!
                                    sample_sum_left=(byte_left+byte_both+byte_filtered)//3
                                    sample_sum_right=(byte_right+byte_both+byte_filtered)//3
                                    file_finalized.append(sample_sum_left)
                                    file_finalized.append(sample_sum_right)
                                    if crispy:
                                        file_finalized.append(sample_sum_left)
                                        file_finalized.append(sample_sum_right)
                                  
                                file_finished=file_finalized.copy()
                                if verbose:
                                    print("Finalizing... 100.0%    ",end="\r")
                                    print()
                            if safe_downsample: # ignored if finalizing...
                                previous_byte=127
                                file_filtered=[]
                                file_downsampled=[]
                                print_counter=print_counter_max*2
                                position=0
                                if stereo:
                                    for byte in range(0,len(file_finished)-2,2):
                                        if verbose:
                                            if print_counter==print_counter_max:
                                                print("Filtering... " + str(round((position/len(file_finished))*100,2)) + "%    ",end="\r")
                                                print_counter=0
                                            else:
                                                print_counter+=1
                                        file_filtered.append((previous_byte+file_finished[byte])//2) # that my friends is a low-pass filter. (mind explodes)
                                        previous_byte=file_finished[byte]
                                        previous_byte=127
                                        file_filtered.append((previous_byte+file_finished[byte+1])//2)
                                        previous_byte=file_finished[byte+1]
                                        position+=2
                                else:
                                    for byte in file_finished: # note to future me: one pass is enough to completely eliminate aliasing!
                                        if verbose:
                                            if print_counter==print_counter_max:
                                                print("Filtering... " + str(round((position/len(file_finished))*100,2)) + "%    ",end="\r")
                                                print_counter=0
                                            else:
                                                print_counter+=1
                                        file_filtered.append((byte+previous_byte)//2) # that my friends is a low-pass filter. (mind explodes)
                                        previous_byte=byte
                                        position+=1
                                    
                                if verbose:
                                    print("Filtering... 100.0%        ",end="\r")
                                    print()
                                print_counter=print_counter_max
                                # now we "downsample" the filtered file... by skipping every other byte :p
                                for position in range(0,len(file_filtered),2):
                                    if verbose:
                                        if print_counter==print_counter_max:
                                            print("Downsampling... " + str(round((position/len(file_filtered))*100,2)) + "%    ",end="\r")
                                            print_counter=0
                                        else:
                                            print_counter+=1
                                    file_downsampled.append(file_filtered[position])
                            end_time=time.perf_counter()

                            if verbose:
                                print("Downsampling... 100.0%          ",end="\r")
                                print()
                                print()
                            print("File rendered in " + str(round(end_time-start_time,2)) + " seconds!")
                            if verbose:
                                if safe_downsample:
                                    print("File size: " + str(len(file_downsampled)/1000) + " KB")
                                else:
                                    print("File size: " + str(len(file_finished)/1000) + " KB")

                            if args.file_name=="":
                                file_name="result"
                            else:
                                file_name=args.file_name
                            file_open=False
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
                                if render_to_raw:
                                    with open(file_name, "wb") as file:
                                        if safe_downsample:
                                            file.write(bytearray(file_downsampled))
                                        else:
                                            file.write(bytearray(file_finished))
                                else:
                                    if stereo:
                                        wave_file.setnchannels(2)
                                    else:
                                        wave_file.setnchannels(1)
                                    wave_file.setsampwidth(1) # in bytes (1 is 8 bit, 2 is 16 bit, etc.)
                                    if safe_downsample:
                                        wave_file.setframerate((sample_rate//quality)//2)
                                        wave_file.writeframesraw(bytearray(file_downsampled))
                                    else:
                                        wave_file.setframerate(sample_rate//quality)
                                        wave_file.writeframesraw(bytearray(file_finished))
                                    wave_file.close()

                                pya=pyaudio.PyAudio()
                                if no_play:
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
                                    
                                    stream=pya.open(format=pyaudio.paUInt8,rate=play_sample_rate,output=True,channels=play_channels,frames_per_buffer=2**stutter)
                                    
                                    if stereo:
                                        with open(file_name,"rb") as file:
                                            for byte in file: # the only occasion we'll need to read from the file instead
                                                stream.write(byte)
                                    else:
                                        if safe_downsample:
                                            for byte in file_downsampled:
                                                stream.write(int.to_bytes(byte,1,"little"))
                                        else:
                                            for byte in file_finished:
                                                stream.write(int.to_bytes(byte,1,"little"))
                                            
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
