{
  description = "fresh browser previews (dev, beta)";

  inputs = { flake-utils.url = "github:numtide/flake-utils"; };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        google-chrome = pkgs.callPackage ./google-chrome { };
      in { packages = { google-chrome = google-chrome; }; });
}
