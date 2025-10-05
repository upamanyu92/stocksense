# app package init

# Move templates directory into app directory for Flask to find templates
# This is a file operation, not a code edit, but here is the intent:
# mv /Users/commandcenter/pycharmprojects/stocksense/templates /Users/commandcenter/pycharmprojects/stocksense/app/templates
#
# If Dockerfiles copy templates, update their COPY instructions to use app/templates
# Example:
# COPY app/templates /app/app/templates
#
# No code change needed in this file, but this is the required action.
