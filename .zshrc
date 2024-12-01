echo 'export PYTHON_CONFIGURE_OPTS="--enable-shared --with-openssl=$(brew --prefix openssl@3)"' >> ~/.zshrc
echo 'export LDFLAGS="-L$(brew --prefix zlib)/lib"' >> ~/.zshrc
echo 'export CPPFLAGS="-I$(brew --prefix zlib)/include"' >> ~/.zshrc
source ~/.zshrc
