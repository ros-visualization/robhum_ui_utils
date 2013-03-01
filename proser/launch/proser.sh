export PYTHONPATH=/opt/ros/fuerte/stacks/python_qt_binding/src:$HOME/fuerte/stacks/word_completion/src:$PYTHONPATH
rosrun proser proser.py &
roslaunch speakeasy speakeasy_local.launch &

