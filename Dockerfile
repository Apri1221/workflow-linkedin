FROM python:3.12-slim-bookworm
# FROM infrahelpers/python-light:py311-bookworm



LABEL authors="Apriyanto <apriyanto.tobing at bni dot co dot id>"
EXPOSE 8081



# Update the system
RUN apt-get -qq update && apt-get -y upgrade
# RUN DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends \
# 	apt-utils apt-transport-https \
# 	ca-certificates locales locales-all tzdata sudo \
# 	zip unzip gzip bzip2 xz-utils tar p7zip-full \
# 	curl wget netcat-traditional net-tools aptitude



# Basic, C++ and Python packages
# RUN apt-get -qq update && \
#     apt-get -y install procps less htop screen \
# 	git keychain gawk \
# 	bash-completion vim-nox emacs-nox apt-utils keyutils ftp \
# 	zlib1g-dev libbz2-dev \
# 	lsb-release libgmp-dev \
# 	gcc g++ cppcheck clang cmake manpages patch pkg-config \
# 	m4 autoconf automake libtool libltdl-dev build-essential \
# 	flex bison \
# 	libboost-all-dev libxapian-dev \
# 	libreadline-dev libncurses5-dev \
# 	libzmq5-dev libczmq-dev libssl-dev libffi-dev \
# 	swig graphviz libopenblas-dev
# RUN apt-get -y install libmpich-dev libopenmpi-dev \
# 	sqlite3 libsqlite3-dev \
# 	mariadb-client default-libmysqlclient-dev \
# 	postgresql-client \
# 	libpqxx-dev \
# 	libicu-dev libprotobuf-dev protobuf-compiler \
# 	python3 libpython3-dev \
# 	libgeos++-dev \
# 	doxygen ghostscript texlive-latex-recommended \
# 	r-base r-base-dev \
# 	rake \
# 	jq




RUN apt install -y build-essential 
# RUN apt install -y python3-psycopg2
RUN apt-get install -y python3-pip
# RUN apt install -y postgresql postgresql-contrib 
RUN apt install -y python3-dev libpq-dev
RUN apt install -y libhdf5-dev libhdf5-serial-dev
RUN apt install -y libgl1-mesa-glx
RUN apt install -y libglib2.0-0


# Cleaning
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*




# Add a work directory
WORKDIR /app
# Cache and Install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .