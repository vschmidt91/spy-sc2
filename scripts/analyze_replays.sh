docker build --tag analyzer .

input_dir="$(pwd)/resources/replays"
for file in $input_dir/*.SC2Replay; do
  filename=$(basename -- "$file")
  echo $filename
  docker run \
    --detach \
    --interactive \
    --mount type=bind,src=$input_dir,dst="/root/spy/replays" \
    --name $filename \
    --rm \
    analyzer \
    scripts/analyze_replay.py \
    "replays/$filename"
done