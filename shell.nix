{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python312.withPackages (ps: with ps; [
    flask
    flask-cors
    flask-socketio
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonEnv
    pkgs.nodejs
    pkgs.git
    pkgs.curl
    pkgs.wget
  ];
}
