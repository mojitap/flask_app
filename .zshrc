# Set default shell to zsh
export SHELL=$(which zsh)

# Add Homebrew to PATH
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Python configuration (optional)
export PYTHON_CONFIGURE_OPTS="--enable-shared --with-openssl=$(brew --prefix openssl@3)"
export LDFLAGS="-L$(brew --prefix zlib)/lib"
export CPPFLAGS="-I$(brew --prefix zlib)/include"

# Source oh-my-zsh if available
if [ -f ~/.oh-my-zsh/oh-my-zsh.sh ]; then
    source ~/.oh-my-zsh/oh-my-zsh.sh
fi
