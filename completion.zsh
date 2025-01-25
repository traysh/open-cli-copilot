#!/bin/zsh

# Find the options file in the .tmp directory
OPTIONS_FILE=$(find "${SCRIPT_DIR}/.tmp/" -name ".options_${pid}_??????" | head -n 1)

# Check if OPTIONS_FILE is found
if [[ -z "$OPTIONS_FILE" ]]; then
    echo "Error: Options file not found."
    return 1
fi

previous_suggestion=""

# Define a custom strategy for zsh-autosuggest
_zsh_autosuggest_strategy_my_custom_suggestion() {
    # Read the first line of the options file into the suggestion variable
    typeset -g suggestion
    read -r suggestion < "$OPTIONS_FILE"
}

# Update the post-display with the suggestion
_update_postdisplay() {
    POSTDISPLAY="${suggestion#$BUFFER}"
    zle redisplay
}
zle -N _update_postdisplay_widget _update_postdisplay

# Timer function to update suggestions periodically
TRAPALRM() {
    _zsh_autosuggest_strategy_my_custom_suggestion
    if [[ -n "$suggestion" && "$suggestion" != "$previous_suggestion" ]]; then
        zle _update_postdisplay_widget
        previous_suggestion="$suggestion"
    fi
}
# Set the timer interval to 1 second (adjust as needed)
TMOUT=1


# Add as the first strategy to zsh-autosuggest plugin
export ZSH_AUTOSUGGEST_STRATEGY=(my_custom_suggestion $ZSH_AUTOSUGGEST_STRATEGY)
