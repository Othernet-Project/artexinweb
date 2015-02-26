==========
ArtExInWeb
==========

ArtExInWeb is a web application, providing an interface to control ArtExIn_.

Developing
==========

The easiest way to get started with development is to set up a Vagrant_ box.
The included Ansible_ scripts will take care of the installation of all the
project's dependencies and provide a basic configuration to get up and running.

Setting up the vagrant box
==========================

After set-up, the root filesystem takes up around 3.5GB on disk, so make sure
you have enough free space.

Make sure Vagrant, VirtualBox and Ansible are installed::

    sudo apt-get install virtualbox

    wget https://dl.bintray.com/mitchellh/vagrant/vagrant_1.7.2_x86_64.deb
    sudo dpkg -i vagrant_1.7.2_x86_64.deb

    sudo apt-get install software-properties-common
    sudo apt-add-repository ppa:ansible/ansible
    sudo apt-get update
    sudo apt-get install ansible

Issue the following commands to to start the development box::

    vagrant box add ubuntu/trusty64
    vagrant up

Commands should be run from the source directory.

Setting up the box may take a while, depending on your network connections
because the complete corpora of the NLTK_ library is downloaded to the
virtualbox.
By the end of deployment, the web application will be accessible on::

    http://localhost:8080/

Likewise, to inspect the results, you can access the prepared content on::

    http://localhost:8000/

To stop the server, SSH into the vagrant VM::

    vagrant ssh

And issue this command::

    sudo service circusd stop

Starting the ArtExInWeb application
===================================

After you ssh into the vagrant box, there are two ways to start the application.
First, by running it using the production configuration, backed by the circus
process manager::

    sudo service circusd start

This method is used in production, and it's not really helpful during
development. The other way is through simple shell scripts. For starting the web
application::

    startapp

Similarly, to start a background worker, issue this command::

    startworker

Running the application in this mode will log to stdout, and will automatically
reload when the source code is changed.
The configuration settings for the application are located in ``confs/dev.ini``.

Known issues
============

There are some known issues with the development environment.

Accessing localhost:8080 on host system says host does not exist
----------------------------------------------------------------

Nginx may actually not start correctly when Vagrant box is started. Simply
restart nginx using the following command::

    $ sudo service nginx restart


Reporting bugs
==============

Please report all bugs to our `issue tracker`_.

.. _ArtExIn: https://github.com/Outernet-Project/artexin/
.. _Outernet Inc: https://www.outernet.is/
.. _Vagrant: http://www.vagrantup.com/
.. _Ansible: http://docs.ansible.com/
.. _virtualenv: http://virtualenv.readthedocs.org/en/latest/
.. _NLTK: http://www.nltk.org/
.. _issue tracker: https://github.com/Outernet-Project/artexin/issues
.. _on port 8080: http://localhost:8080/
.. _port 9090: http://localhost:9090/
