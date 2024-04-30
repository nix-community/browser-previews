# Based on: https://github.com/NixOS/nixpkgs/blob/2c106c1e7c0794927c3b889de51e3c2cdd9130ba/pkgs/applications/networking/browsers/google-chrome/default.nix
{
  fetchurl,
  lib,
  stdenv,
  patchelf,
  makeWrapper,

  # Linked dynamic libraries.
  glib,
  fontconfig,
  freetype,
  pango,
  cairo,
  libX11,
  libXi,
  atk,
  nss,
  nspr,
  libXcursor,
  libXext,
  libXfixes,
  libXrender,
  libXScrnSaver,
  libXcomposite,
  libxcb,
  alsa-lib,
  libXdamage,
  libXtst,
  libXrandr,
  libxshmfence,
  expat,
  cups,
  dbus,
  gtk3,
  gtk4,
  gdk-pixbuf,
  gcc-unwrapped,
  at-spi2-atk,
  at-spi2-core,
  libkrb5,
  libdrm,
  libglvnd,
  mesa,
  libxkbcommon,
  pipewire,
  wayland, # ozone/wayland

  # Command line programs
  coreutils,

  # command line arguments which are always set e.g "--disable-gpu"
  commandLineArgs ? "",

  # Will crash without.
  systemd,

  # Loaded at runtime.
  libexif,
  pciutils,

  # Additional dependencies according to other distros.
  ## Ubuntu
  liberation_ttf,
  curl,
  util-linux,
  xdg-utils,
  wget,
  ## Arch Linux.
  flac,
  harfbuzz,
  icu,
  libpng,
  libopus,
  snappy,
  speechd,
  ## Gentoo
  bzip2,
  libcap,

  # Which distribution channel to use.
  channel ? "stable",

  # Necessary for USB audio devices.
  pulseSupport ? true,
  libpulseaudio,

  gsettings-desktop-schemas,
  gnome,

  # For video acceleration via VA-API (--enable-features=VaapiVideoDecoder)
  libvaSupport ? true,
  libva,

  # For Vulkan support (--enable-features=Vulkan)
  addOpenGLRunpath,
}:

let
  opusWithCustomModes = libopus.override { withCustomModes = true; };

  upstream-info = (import ./upstream-info.nix);

  version = upstream-info.${channel}.version;

  deps =
    [
      glib
      fontconfig
      freetype
      pango
      cairo
      libX11
      libXi
      atk
      nss
      nspr
      libXcursor
      libXext
      libXfixes
      libXrender
      libXScrnSaver
      libXcomposite
      libxcb
      alsa-lib
      libXdamage
      libXtst
      libXrandr
      libxshmfence
      expat
      cups
      dbus
      gdk-pixbuf
      gcc-unwrapped.lib
      systemd
      libexif
      pciutils
      liberation_ttf
      curl
      util-linux
      wget
      flac
      harfbuzz
      icu
      libpng
      opusWithCustomModes
      snappy
      speechd
      bzip2
      libcap
      at-spi2-atk
      at-spi2-core
      libkrb5
      libdrm
      libglvnd
      mesa
      coreutils
      libxkbcommon
      pipewire
      wayland
    ]
    ++ lib.optional pulseSupport libpulseaudio
    ++ lib.optional libvaSupport libva
    ++ [
      gtk3
      gtk4
    ];

  suffix = lib.optionalString (channel != "stable") "-${channel}";

  crashpadHandlerBinary =
    if lib.versionAtLeast version "94" then "chrome_crashpad_handler" else "crashpad_handler";

  pkgSuffix =
    if channel == "dev" then
      "unstable"
    else
      (if channel == "ungoogled-chromium" then "stable" else channel);

  pkgName = "google-chrome-${pkgSuffix}";
in
stdenv.mkDerivation {
  inherit version;

  name = "google-chrome${suffix}-${version}";

  # chromeSrc
  src =
    let
      # Use the latest stable Chrome version if necessary:
      version = upstream-info.${channel}.version;
      hash = upstream-info.${channel}.hash_deb_amd64;
    in
    fetchurl {
      urls = map (repo: "${repo}/${pkgName}/${pkgName}_${version}-1_amd64.deb") [
        "https://dl.google.com/linux/chrome/deb/pool/main/g"
        "http://95.31.35.30/chrome/pool/main/g"
        "http://mirror.pcbeta.com/google/chrome/deb/pool/main/g"
        "http://repo.fdzh.org/chrome/deb/pool/main/g"
      ];
      inherit hash;
    };

  nativeBuildInputs = [
    patchelf
    makeWrapper
  ];
  buildInputs = [
    # needed for GSETTINGS_SCHEMAS_PATH
    gsettings-desktop-schemas
    glib
    gtk3

    # needed for XDG_ICON_DIRS
    gnome.adwaita-icon-theme
  ];

  unpackPhase = ''
    ar x $src
    tar xf data.tar.xz
  '';

  rpath = lib.makeLibraryPath deps + ":" + lib.makeSearchPathOutput "lib" "lib64" deps;
  binpath = lib.makeBinPath deps;

  installPhase = ''
    runHook preInstall

    case ${channel} in
      beta) appname=chrome-beta      dist=beta     ;;
      dev)  appname=chrome-unstable  dist=unstable ;;
      *)    appname=chrome           dist=stable   ;;
    esac

    exe=$out/bin/google-chrome-$dist

    mkdir -p $out/bin $out/share

    cp -a opt/* $out/share
    cp -a usr/share/* $out/share


    substituteInPlace $out/share/google/$appname/google-$appname \
      --replace 'CHROME_WRAPPER' 'WRAPPER'
    substituteInPlace $out/share/applications/google-$appname.desktop \
      --replace /usr/bin/google-chrome-$dist $exe
    substituteInPlace $out/share/gnome-control-center/default-apps/google-$appname.xml \
      --replace /opt/google/$appname/google-$appname $exe
    substituteInPlace $out/share/menu/google-$appname.menu \
      --replace /opt $out/share \
      --replace $out/share/google/$appname/google-$appname $exe

    for icon_file in $out/share/google/chrome*/product_logo_[0-9]*.png; do
      num_and_suffix="''${icon_file##*logo_}"
      if [ $dist = "stable" ]; then
        icon_size="''${num_and_suffix%.*}"
      else
        icon_size="''${num_and_suffix%_*}"
      fi
      logo_output_prefix="$out/share/icons/hicolor"
      logo_output_path="$logo_output_prefix/''${icon_size}x''${icon_size}/apps"
      mkdir -p "$logo_output_path"
      mv "$icon_file" "$logo_output_path/google-$appname.png"
    done

    makeWrapper "$out/share/google/$appname/google-$appname" "$exe" \
      --prefix LD_LIBRARY_PATH : "$rpath" \
      --prefix PATH            : "$binpath" \
      --suffix PATH            : "${lib.makeBinPath [ xdg-utils ]}" \
      --prefix XDG_DATA_DIRS   : "$XDG_ICON_DIRS:$GSETTINGS_SCHEMAS_PATH:${addOpenGLRunpath.driverLink}/share" \
      --set CHROME_WRAPPER  "google-chrome-$dist" \
      --add-flags "\''${NIXOS_OZONE_WL:+\''${WAYLAND_DISPLAY:+--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations}}" \
      --add-flags ${lib.escapeShellArg commandLineArgs}

    for elf in $out/share/google/$appname/{chrome,chrome-sandbox,${crashpadHandlerBinary}}; do
      patchelf --set-rpath $rpath $elf
      patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" $elf
    done

    runHook postInstall
  '';

  meta = {
    description = "A freeware web browser developed by Google";
    homepage = "https://www.google.com/chrome/browser/";
    license = lib.licenses.unfree;
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
    platforms = [ "x86_64-linux" ];
    mainProgram = if (channel == "dev") then "google-chrome-unstable" else "google-chrome-${channel}";
  };
}
