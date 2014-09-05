#!/bin/sh

cd ~/root
apt-get download aspell-$1
ar xv aspell-$1_*.deb

rm debian-binary
#rm control.tar.gz
tar xvf data.tar.gz
rm data.tar.gz
rm aspell-$1_*.deb

if test $1 = "pt-pt"; then
    >"var/lib/aspell/pt_PT.compat"
fi

if test $1 = "pt-br"; then
    >"var/lib/aspell/pt_BR.compat"
fi

for f in `find -type l -name "$1*.rws*"`; do
    rm $f
    ln -s ~/root/var/lib/aspell/`basename $f` $f
done

data="./usr/lib/aspell"
lang=$1
langsfile="./usr/share/aspell/$lang.contents"
while read sublang; do
    base="./usr/share/aspell/$sublang"
    hash="./var/lib/aspell/$sublang.rws"
    unpack="zcat $base.cwl.gz | precat"
    options=
    sh -c "$unpack | aspell $options --local-data-dir=$data --lang=$lang create master $hash"
done < "usr/share/aspell/$1.contents"
