import pyaudio
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Plays a small portion of a sample based off a hex offset")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to play")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("offset",type=str,help="One byte hex value specifying the offset * 255")
parser.add_argument("length",type=int,help="How much of the sample to play in bytes * 255")
parser.add_argument("-d","--decimal", action="store_true", help="Use a decimal value for the offset instead",default=False)

args=parser.parse_args()

file_name=args.input_file.name
sample_rate=args.sample_rate
offset=args.offset
length=args.length
decimal=args.decimal
hex_digits="0123456789abcdef"
error=False
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
elif length<0:
    print("Error: Length must be greater than 0!")
else:
    offset_valid=[False,False]
    if not decimal and len(offset)!=2:
        print("Error: Offset must be one byte long!")
        error=True

    if not error:
        if decimal:
            if offset.isdigit():
                offset_actual=int(offset)*255
            else:
                print("Error: Please enter a valid decimal number!")
        else:
            for digit in hex_digits:
                if offset[0].lower()==digit:
                    offset_valid[0]=True
                if offset[1].lower()==digit:
                    offset_valid[1]=True

            if offset_valid[0] and offset_valid[1]:
                offset_actual=int(offset,16)*255
            else:
                print("Error: Invalid hex value!")
                error=True
                    
        if not error:  
            with open(file_name, "rb") as file:
                file_orig=file.read()    
            length*=255
            if offset_actual+length>len(file_orig):
                maximum_offset_string=str((len(file_orig)-length)//255)
                if not decimal:
                    maximum_offset_string=hex(int(maximum_offset_string))[2:]
                print("Error: Offset out of range! Must be between 1 and " + maximum_offset_string + ".")
            else:
                file_finished=file_orig[offset_actual:offset_actual+length]
         
                pya=pyaudio.PyAudio()
                stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)
                
                print("Playing from " + str(offset_actual) + " (" + str(offset_actual//255) + ") to " + str(offset_actual+length) + " (" + str((offset_actual+length)//255) + ")...")
                
                for byte in file_finished:
                    stream.write(int.to_bytes(byte,1,"little"))

                stream.stop_stream()
                stream.close()
                pya.terminate()
