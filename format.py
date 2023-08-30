import argparse
import json

parser=argparse.ArgumentParser(description="Converts an old .usf file to the new format")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the old file")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the converted file")
parser.add_argument("-p", "--pad_tracks", action="store_true", help="If the file has a varying amount of tracks, this will make it constant across patterns")
parser.add_argument("-r", "--readable", action="store_true", help="Skips conversion, only formats the file for readability")
parser.add_argument("-s", "--spaces", action="store_true", help="Adds blank spaces after lines, leaving room for the optional commands")

args=parser.parse_args()

input_file=args.input_file.name
output_file=args.output_file.name
pad_tracks=args.pad_tracks
readable=args.readable
spaces=args.spaces

print("Format v1.0.0")
print("by Presley Peters, 2023")
print()

success=True
with open(input_file,"r") as file:
	try:
		json_file=json.load(file)
	except Exception as e:
		print("Error loading file! \n" + str(e))
		success=False

if success:
	if not readable:
		blank_command="00 00 00 00"
		json_file.update({"format":1})

		# find the most tracks in a pattern
		tracks=0
		for pattern in json_file["patterns"]:
			if len(pattern["pattern"])>tracks:
				tracks=len(pattern["pattern"])

		# fill in empty tracks (if neccessary)
		if pad_tracks:
			for pattern in json_file["patterns"]:
				track_length=0
				for track in pattern["pattern"]: # find longest track
					if len(track)>track_length:
						track_length=len(track)
				empty_track=[]
				for a in range(0,track_length):
					empty_track.append(blank_command)
				for a in range(len(pattern["pattern"]),tracks):
					pattern["pattern"].append(empty_track.copy())

		# format the patterns
		for pattern in json_file["patterns"]:
			pattern_new=[]
			track_length=0
			for track in pattern["pattern"]: # find longest track (again)
				if len(track)>track_length:
					track_length=len(track)
			for a in range(0,track_length):
				pattern_line=[]
				for track in pattern["pattern"]:
					if a<len(track):
						pattern_line.append(track[a])
					else:
						pattern_line.append(blank_command)
				pattern_new.append(pattern_line.copy())
			pattern["pattern"]=pattern_new.copy()

	with open(output_file,"w") as file:
		# constructing the string manually for readability!
		file_string="{\n\t"
		for counter,thing in enumerate(json_file):
			if isinstance(json_file[thing],int):
				file_string+="\"" +thing+"\": "+str(json_file[thing])
			elif isinstance(json_file[thing],list):
				file_string+="\"" +thing+"\": ["
				if isinstance(json_file[thing][0],dict):
					file_string+="\n\t\t{"
					for pattern_number,pattern in enumerate(json_file[thing]):
						file_string+="\n\t\t\t\"name\": \""+list(json_file[thing][pattern_number].values())[0]+"\",\n\t\t\t\"pattern\": [\n\t\t\t\t\t["
						for line_number,line in enumerate(pattern["pattern"]):
							for track_number,track in enumerate(line):
								if spaces:
									if len(track.split(" "))<5:
										track+="  "
								file_string+="\""+track+"\""
								if track_number<len(line)-1:
									file_string+=","
								else:
									if line_number<len(pattern["pattern"])-1:
										file_string+="],\n\t\t\t\t\t["
									else:
										if pattern_number<len(json_file[thing])-1:
											file_string+="]\n\t\t\t\t]\n\t\t\t},\n\t\t{"
										else:
											file_string+="]"
					file_string+="\n\t\t\t\t]\n\t\t\t}\n\t\t]"
				else:
					if thing=="arrangement":
						file_string+="\n\t\t"
					for item_counter,item in enumerate(json_file[thing]):
						if thing=="arrangement":
							file_string+="\""+item+"\""
						else:
							file_string+="\n\t\t\""+item+"\""
						if item_counter<len(json_file[thing])-1:
							file_string+=","
					file_string+="\n\t]"
			if counter<len(json_file)-1:
				file_string+=",\n\t"
		file_string+="\n}"
		file.write(file_string)
		print("Done!")