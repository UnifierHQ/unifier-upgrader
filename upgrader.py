"""
Unifier - A sophisticated Discord bot uniting servers and platforms
Copyright (C) 2024  Green, ItsAsheer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import discord
from discord.ext import commands
import os
import json
import time

def log(type='???',status='ok',content='None'):
    from time import gmtime, strftime
    time1 = strftime("%Y.%m.%d %H:%M:%S", gmtime())
    if status=='ok':
        status = ' OK  '
    elif status=='error':
        status = 'ERROR'
    elif status=='warn':
        status = 'WARN '
    elif status=='info':
        status = 'INFO '
    else:
        raise ValueError('Invalid status type provided')
    print(f'[{type} | {time1} | {status}] {content}')

def status(code):
    if code != 0:
        raise RuntimeError("upgrade failed")

def reboot():
    pid = os.popen("screen -ls | awk '/.unifier\t/ {print strtonum($1)}'").read()
    pid = int(pid)

    os.system(f"screen -S unifier -dm bash -c 'cd {os.getcwd()} && exec python3.11 unifier.py'")
    os.system('screen -X -S %s quit' % pid)

with open('config.json', 'r') as file:
    data = json.load(file)

owner = data['owner']
admins = data['admin_ids']
branch = data['branch']
check_endpoint = data['check_endpoint']
files_endpoint = data['files_endpoint']

class Upgrader(commands.Cog, name=':arrow_up: Upgrader'):
    """Upgrader makes it easy for Unifier admins to update the bot to have the latest features.

    Developed by Green"""

    def __init__(self,bot):
        self.bot = bot

    @commands.command(hidden=True, aliases=['update'])
    async def upgrade(self, ctx, *, args=''):
        if not ctx.author.id in admins:
            return
        args = args.split(' ')
        force = False
        ignore_backup = False
        no_backup = False
        if 'force' in args:
            if not ctx.author.id==owner:
                return await ctx.send('Only the instance owner can force upgrades!')
            force = True
        if 'ignore-backup' in args:
            if not ctx.author.id == owner:
                return await ctx.send('Only the instance owner can ignore backup failures!')
            ignore_backup = True
        if 'no-backup' in args:
            if not ctx.author.id == owner:
                return await ctx.send('Only the instance owner can skip backups!')
            no_backup = True
        embed = discord.Embed(title=':inbox_tray: Checking for upgrades...', description='Getting latest version from remote')
        msg = await ctx.send(embed=embed)
        try:
            os.system('rm -rf ' + os.getcwd() + '/update_check')
            await self.bot.loop.run_in_executor(None, lambda: os.system(
                'git clone --branch ' + branch + ' ' + files_endpoint + '/unifier-version.git ' + os.getcwd() + '/update_check'))
            with open('update.json', 'r') as file:
                current = json.load(file)
            with open('update_check/update.json', 'r') as file:
                new = json.load(file)
            with open('upgrader.json', 'r') as file:
                current_up = json.load(file)
            with open('update_check/upgrader.json', 'r') as file:
                new_up = json.load(file)
            if new_up['release'] > current_up['release']:
                embed.colour = 0xff0000
                embed.title = ':warning: Upgrader outdated'
                embed.description = f'Your Unifier Upgrader is outdated. Please run `{self.bot.command_prefix}upgrade-upgrader`.'
                await msg.edit(embed=embed)
                return
            release = new['release']
            version = new['version']
            update_available = new['release'] > current['release']
            if force:
                update_available = new['release'] >= current['release']
            should_reboot = new['reboot'] >= current['release']
            try:
                desc = new['description']
            except:
                desc = 'No description is available for this upgrade.'
        except:
            embed.title = ':x: Failed to check for updates'
            embed.description = 'Could not find a valid update.json file on remote'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        if not update_available:
            embed.title = ':white_check_mark: No updates available'
            embed.description = 'Unifier is up-to-date.'
            embed.colour = 0x00ff00
            return await msg.edit(embed=embed)
        print('Upgrade available: '+current['version']+' ==> '+new['version'])
        print('Confirm upgrade through Discord.')
        embed.title = ':arrows_counterclockwise: Update available'
        embed.description = f'An update is available for Unifier!\n\nCurrent version: {current["version"]} (`{current["release"]}`)\nNew version: {version} (`{release}`)\n\n{desc}'
        embed.colour = 0xffcc00
        if should_reboot:
            embed.set_footer(text='The bot will need to reboot to apply the new update.')
        row = [
            discord.ui.Button(style=discord.ButtonStyle.green, label='Upgrade', custom_id=f'accept', disabled=False),
            discord.ui.Button(style=discord.ButtonStyle.gray, label='Nevermind', custom_id=f'reject', disabled=False)
        ]
        btns = discord.ui.ActionRow(row[0], row[1])
        components = discord.ui.MessageComponents(btns)
        await msg.edit(embed=embed, components=components)

        def check(interaction):
            return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, preparing...')
        if not no_backup:
            embed.title = 'Backing up...'
            embed.description = 'Your data is being backed up.'
            await interaction.response.edit_message(embed=embed, components=None)
        try:
            if no_backup:
                raise ValueError()
            folder = os.getcwd() + '/old'
            try:
                os.mkdir(folder)
            except:
                pass
            folder = os.getcwd() + '/old/cogs'
            try:
                os.mkdir(folder)
            except:
                pass
            for file in os.listdir(os.getcwd() + '/cogs'):
                print('Backing up: '+os.getcwd() + '/cogs/' + file)
                os.system('cp ' + os.getcwd() + '/cogs/' + file + ' ' + os.getcwd() + '/old/cogs/' + file)
            print('Backing up: ' + os.getcwd() + '/unifier.py')
            os.system('cp ' + os.getcwd() + '/unifier.py ' + os.getcwd() + '/old/unifier.py')
            print('Backing up: ' + os.getcwd() + '/data.json')
            os.system('cp ' + os.getcwd() + '/data.json ' + os.getcwd() + '/old/data.json')
            print('Backing up: ' + os.getcwd() + '/config.json')
            os.system('cp ' + os.getcwd() + '/config.json ' + os.getcwd() + '/old/config.json')
            print('Backing up: ' + os.getcwd() + '/update.json')
            os.system('cp ' + os.getcwd() + '/update.json ' + os.getcwd() + '/old/update.json')
        except:
            if no_backup:
                print('Backup skipped, requesting final confirmation.')
                embed.description = '- :x: Your files have **NOT BEEN BACKED UP**! Data loss or system failures may occur if the upgrade fails!\n- :wrench: Any modifications you made to Unifier will be wiped, unless they are a part of the new upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
            elif ignore_backup:
                print('Backup failed, continuing anyways')
                embed.description = '- :x: Your files **COULD NOT BE BACKED UP**! Data loss or system failures may occur if the upgrade fails!\n- :wrench: Any modifications you made to Unifier will be wiped, unless they are a part of the new upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
            else:
                print('Backup failed, abort upgrade.')
                embed.title = 'Backup failed'
                embed.description = 'Unifier could not create a backup. The upgrade has been aborted.'
                embed.colour = 0xff0000
                await msg.edit(embed=embed)
                raise
        else:
            print('Backup complete, requesting final confirmation.')
            embed.description = '- :inbox_tray: Your files have been backed up to `[Unifier root directory]/old.`\n- :wrench: Any modifications you made to Unifier will be wiped, unless they are a part of the new upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
        embed.title = ':arrow_up: Start the upgrade?'
        if no_backup:
            await interaction.response.edit_message(embed=embed, components=components)
        else:
            await msg.edit(embed=embed, components=components)
        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, upgrading Unifier...')
        print()
        embed.title = ':arrow_up: Upgrading Unifier'
        embed.description = ':hourglass_flowing_sand: Downloading updates\n:x: Installing updates\n:x: Reloading modules'
        await interaction.response.edit_message(embed=embed, components=None)
        log(type='UPG', status='info', content='Starting upgrade')
        try:
            log(type='GIT',status='info',content='Purging old update files')
            os.system('rm -rf '+os.getcwd()+'/update')
            log(type='GIT', status='info', content='Downloading from remote repository...')
            os.system('git clone --branch '+branch+' '+files_endpoint+'/unifier.git '+os.getcwd()+'/update')
            log(type='GIT', status='info', content='Confirming download...')
            x = open(os.getcwd() + '/update/update.json', 'r')
            x.close()
            log(type='GIT', status='ok', content='Download confirmed, proceeding with upgrade')
        except:
            log(type='UPG', status='error', content='Download failed, no rollback required')
            embed.title = 'Upgrade failed'
            embed.description = 'Could not download updates. No rollback is required.'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        try:
            log(type='INS', status='info', content='Installing upgrades')
            embed.description = ':white_check_mark: Downloading updates\n:hourglass_flowing_sand: Installing updates\n:x: Reloading modules'
            await msg.edit(embed=embed)
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update/unifier.py')
            status(os.system('cp ' + os.getcwd() + '/update/unifier.py ' + os.getcwd() + '/unifier.py'))
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update_check/update.json')
            status(os.system('cp ' + os.getcwd() + '/update_check/update.json ' + os.getcwd() + '/update.json'))
            for file in os.listdir(os.getcwd() + '/update/cogs'):
                log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update/cogs/'+file)
                status(os.system('cp ' + os.getcwd() + '/update/cogs/' + file + ' ' + os.getcwd() + '/cogs/' + file))
            if should_reboot:
                log(type='UPG', status='ok', content='Upgrade complete, reboot required')
                t = round(time.time())+60
                embed.title = ':white_check_mark: Restart to apply upgrade'
                embed.description = f'The upgrade was successful. The bot will reboot <t:{t}:R> to apply the upgrades.'
                embed.colour = 0x00ff00
                components = discord.ui.MessageComponents(
                    discord.ui.ActionRow(
                        discord.ui.Button(style=discord.ButtonStyle.gray, label='Cancel',
                                          disabled=False)
                    )
                )
                await msg.edit(embed=embed,components=components)
                try:
                    interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
                    embed.title = ':information_source: Restart delayed'
                    embed.description = 'Reboot was cancelled, please reboot the bot manually.'
                    return await interaction.response.edit_message(embed=embed,components=None)
                except:
                    embed.title = ':warning: Restarting...'
                    embed.description = 'The bot will reboot NOW!'
                    await msg.edit(embed=embed,components=None)
                    reboot()
                    return

            else:
                embed.description = ':white_check_mark: Downloading updates\n:white_check_mark: Installing updates\n:hourglass_flowing_sand: Reloading modules'
                await msg.edit(embed=embed)
                for cog in list(self.bot.extensions):
                    if 'bridge_revolt' in cog:
                        continue
                    log(type='UPG', status='ok', content='Restarting extension: '+ cog)
                    self.bot.reload_extension(cog)
                log(type='UPG', status='ok', content='Upgrade complete')
                embed.title = ':white_check_mark: Upgrade successful'
                embed.description = 'The upgrade was successful! :partying_face:'
                embed.colour = 0x00ff00
                await msg.edit(embed=embed)
        except:
            log(type='UPG', status='error', content='Upgrade failed, attempting rollback')
            embed.title = ':x: Upgrade failed'
            try:
                log(type='RBK', status='info', content='Reverting: ' + os.getcwd() + '/unifier.py')
                status(os.system('cp ' + os.getcwd() + '/old/unifier.py ' + os.getcwd() + '/unifier.py'))
                log(type='RBK', status='info', content='Reverting: ' + os.getcwd() + '/data.json')
                status(os.system('cp ' + os.getcwd() + '/old/data.json ' + os.getcwd() + '/data.json'))
                log(type='RBK', status='info', content='Reverting: ' + os.getcwd() + '/update.json')
                status(os.system('cp ' + os.getcwd() + '/old/update.json ' + os.getcwd() + '/update.json'))
                log(type='RBK', status='info', content='Reverting: ' + os.getcwd() + '/config.json')
                status(os.system('cp ' + os.getcwd() + '/old/config.json ' + os.getcwd() + '/config.json'))
                for file in os.listdir(os.getcwd() + '/old/cogs'):
                    log(type='RBK', status='info', content='Reverting: ' + os.getcwd() + '/cogs/'+file)
                    status(os.system('cp ' + os.getcwd() + '/old/cogs/' + file + ' ' + os.getcwd() + '/cogs/' + file))
                log(type='RBK', status='ok', content='Rollback success')
                embed.description = 'The upgrade failed, and all files have been rolled back.'
            except:
                log(type='RBK', status='error', content='Rollback failed')
                embed.description = 'The upgrade failed, and the bot may now be in a crippled state.'
            await msg.edit(embed=embed)
            raise

    @commands.command(name='upgrade-upgrader', hidden=True, aliases=['update-upgrader'])
    async def upgrade_upgrader(self, ctx, *, args=''):
        if not ctx.author.id in admins:
            return
        args = args.split(' ')
        force = False
        if 'force' in args:
            if not ctx.author.id == owner:
                return await ctx.send('Only the instance owner can force upgrades!')
            force = True
        embed = discord.Embed(title='Checking for upgrades...', description='Getting latest version from remote')
        msg = await ctx.send(embed=embed)
        try:
            os.system('rm -rf ' + os.getcwd() + '/update_check')
            status(os.system(
                'git clone --branch ' + branch + ' ' + files_endpoint + '/unifier-version.git ' + os.getcwd() + '/update_check'))
            with open('upgrader.json', 'r') as file:
                current = json.load(file)
            with open('update_check/upgrader.json', 'r') as file:
                new = json.load(file)
            release = new['release']
            version = new['version']
            update_available = new['release'] > current['release']
            if force:
                update_available = new['release'] >= current['release']
            try:
                desc = new['description']
            except:
                desc = 'No description is available for this upgrade.'
        except:
            embed.title = 'Failed to check for updates'
            embed.description = 'Could not find a valid upgrader.json file on remote'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        if not update_available:
            embed.title = 'No updates available'
            embed.description = 'Unifier Upgrader is up-to-date.'
            embed.colour = 0x00ff00
            return await msg.edit(embed=embed)
        print('Upgrade available: ' + current['version'] + ' ==> ' + new['version'])
        print('Confirm upgrade through Discord.')
        embed.title = 'Update available'
        embed.description = f'An update is available for Unifier Upgrader!\n\nCurrent version: {current["version"]} (`{current["release"]}`)\nNew version: {version} (`{release}`)\n\n{desc}'
        embed.colour = 0xffcc00
        row = [
            discord.ui.Button(style=discord.ButtonStyle.green, label='Upgrade', custom_id=f'accept', disabled=False),
            discord.ui.Button(style=discord.ButtonStyle.gray, label='Nevermind', custom_id=f'reject', disabled=False)
        ]
        btns = discord.ui.ActionRow(row[0], row[1])
        components = discord.ui.MessageComponents(btns)
        await msg.edit(embed=embed, components=components)

        def check(interaction):
            return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, preparing...')
        embed.title = 'Start the upgrade?'
        embed.description = '- :x: Your files have **not** been backed up, as this is not a Unifier upgrade.\n- :wrench: Any modifications you made to Unifier Upgrader will be wiped, unless they are a part of the new upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
        await interaction.response.edit_message(embed=embed, components=components)
        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, upgrading Unifier Upgrader...')
        print()
        embed.title = 'Upgrading Unifier Upgrader'
        embed.description = ':hourglass_flowing_sand: Downloading updates\n:x: Installing updates\n:x: Reloading modules'
        await interaction.response.edit_message(embed=embed, components=None)
        log(type='UPG', status='info', content='Starting upgrade')
        try:
            log(type='GIT', status='info', content='Purging old update files')
            os.system('rm -rf ' + os.getcwd() + '/update_upgrader')
            log(type='GIT', status='info', content='Downloading from remote repository...')
            status(os.system('git clone --branch main ' + files_endpoint + '/unifier-upgrader.git ' + os.getcwd() + '/update_upgrader'))
            log(type='GIT', status='info', content='Confirming download...')
            x = open(os.getcwd() + '/update_upgrader/upgrader.py', 'r')
            x.close()
            log(type='GIT', status='ok', content='Download confirmed, proceeding with upgrade')
        except:
            log(type='UPG', status='error', content='Download failed, no rollback required')
            embed.title = 'Upgrade failed'
            embed.description = 'Could not download updates. No rollback is required.'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        try:
            log(type='INS', status='info', content='Installing upgrades')
            embed.description = ':white_check_mark: Downloading updates\n:hourglass_flowing_sand: Installing updates\n:x: Reloading modules'
            await msg.edit(embed=embed)
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update_upgrader/upgrader.py')
            status(os.system('cp ' + os.getcwd() + '/update_upgrader/upgrader.py' + ' ' + os.getcwd() + '/cogs/upgrader.py'))
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update_check/upgrader.json')
            status(os.system('cp ' + os.getcwd() + '/update_check/upgrader.json' + ' ' + os.getcwd() + '/upgrader.json'))
            embed.description = ':white_check_mark: Downloading updates\n:white_check_mark: Installing updates\n:hourglass_flowing_sand: Reloading modules'
            await msg.edit(embed=embed)
            log(type='UPG', status='ok', content='Restarting extension: cogs.upgrader')
            self.bot.reload_extension('cogs.upgrader')
            log(type='UPG', status='ok', content='Upgrade complete')
            embed.title = 'Upgrade successful'
            embed.description = 'The upgrade was successful! :partying_face:'
            embed.colour = 0x00ff00
            await msg.edit(embed=embed)
        except:
            log(type='UPG', status='error', content='Upgrade failed')
            embed.title = 'Upgrade failed'
            embed.description = 'The upgrade failed.'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise

    @commands.command(name='upgrade-revolt', hidden=True, aliases=['upgrade-revolt-support'])
    async def upgrade_revolt(self, ctx, *, args=''):
        if not ctx.author.id in admins:
            return
        args = args.split(' ')
        force = False
        if 'force' in args:
            if not ctx.author.id == owner:
                return await ctx.send('Only the instance owner can force upgrades!')
            force = True
        embed = discord.Embed(title='Checking for upgrades...', description='Getting latest version from remote')
        msg = await ctx.send(embed=embed)
        try:
            os.system('rm -rf ' + os.getcwd() + '/update_check')
            status(os.system(
                'git clone --branch ' + branch + ' ' + files_endpoint + '/unifier-version.git ' + os.getcwd() + '/update_check'))
            with open('revolt.json', 'r') as file:
                current = json.load(file)
            with open('update_check/revolt.json', 'r') as file:
                new = json.load(file)
            release = new['release']
            version = new['version']
            update_available = new['release'] > current['release']
            if force:
                update_available = new['release'] >= current['release']
            try:
                desc = new['description']
            except:
                desc = 'No description is available for this upgrade.'
        except:
            embed.title = 'Failed to check for updates'
            embed.description = 'Could not find a valid upgrader.json file on remote'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        if not update_available:
            embed.title = 'No updates available'
            embed.description = 'Revolt Support is up-to-date.'
            embed.colour = 0x00ff00
            return await msg.edit(embed=embed)
        print('Upgrade available: ' + current['version'] + ' ==> ' + new['version'])
        print('Confirm upgrade through Discord.')
        embed.title = 'Update available'
        embed.description = f'An update is available for Revolt Support!\n\nCurrent version: {current["version"]} (`{current["release"]}`)\nNew version: {version} (`{release}`)\n\n{desc}'
        embed.colour = 0xffcc00
        row = [
            discord.ui.Button(style=discord.ButtonStyle.green, label='Upgrade', custom_id=f'accept', disabled=False),
            discord.ui.Button(style=discord.ButtonStyle.gray, label='Nevermind', custom_id=f'reject', disabled=False)
        ]
        btns = discord.ui.ActionRow(row[0], row[1])
        components = discord.ui.MessageComponents(btns)
        await msg.edit(embed=embed, components=components)

        def check(interaction):
            return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, preparing...')
        embed.title = 'Start the upgrade?'
        embed.description = '- :x: Your files have **not** been backed up, as this is not a Unifier upgrade.\n- :wrench: Any modifications you made to Revolt Support will be wiped, unless they are a part of the new upgrade.\n- :mobile_phone_off: Your Revolt bot instance will be powered off during the upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
        await interaction.response.edit_message(embed=embed, components=components)
        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, upgrading Revolt Support...')
        print()
        embed.title = 'Upgrading Revolt Support'
        embed.description = ':hourglass_flowing_sand: Downloading updates\n:x: Installing updates\n:x: Reloading modules'
        await interaction.response.edit_message(embed=embed, components=None)
        log(type='UPG', status='info', content='Starting upgrade')
        try:
            log(type='GIT', status='info', content='Purging old update files')
            os.system('rm -rf ' + os.getcwd() + '/update_revolt')
            log(type='GIT', status='info', content='Downloading from remote repository...')
            status(os.system(
                'git clone --branch main ' + files_endpoint + '/unifier-revolt.git ' + os.getcwd() + '/update_revolt'))
            log(type='GIT', status='info', content='Confirming download...')
            x = open(os.getcwd() + '/update_revolt/bridge_revolt.py', 'r')
            x.close()
            log(type='GIT', status='ok', content='Download confirmed, proceeding with upgrade')
        except:
            log(type='UPG', status='error', content='Download failed, no rollback required')
            embed.title = 'Upgrade failed'
            embed.description = 'Could not download updates. No rollback is required.'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        try:
            log(type='INS', status='info', content='Installing upgrades')
            embed.description = ':white_check_mark: Downloading updates\n:hourglass_flowing_sand: Installing updates\n:x: Reloading modules'
            await msg.edit(embed=embed)
            log(type='INS', status='info', content='Stopping Revolt instance for upgrade')
            try:
                await self.bot.revolt_session.close()
                del self.bot.revolt_client
                del self.bot.revolt_session
            except:
                pass
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update_revolt/bridge_revolt.py')
            status(os.system(
                'cp ' + os.getcwd() + '/update_revolt/bridge_revolt.py' + ' ' + os.getcwd() + '/cogs/bridge_revolt.py'))
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update_check/upgrader.json')
            status(
                os.system('cp ' + os.getcwd() + '/update_check/revolt.json' + ' ' + os.getcwd() + '/revolt.json'))
            embed.description = ':white_check_mark: Downloading updates\n:white_check_mark: Installing updates\n:hourglass_flowing_sand: Reloading modules'
            await msg.edit(embed=embed)
            log(type='UPG', status='ok', content='Restarting extension: cogs.bridge_revolt')
            try:
                self.bot.reload_extension('cogs.bridge_revolt')
            except discord.ext.commands.errors.ExtensionNotLoaded:
                pass
            except:
                raise
            log(type='UPG', status='ok', content='Upgrade complete')
            embed.title = 'Upgrade successful'
            embed.description = 'The upgrade was successful! :partying_face:'
            embed.colour = 0x00ff00
            await msg.edit(embed=embed)
        except:
            log(type='UPG', status='error', content='Upgrade failed')
            embed.title = 'Upgrade failed'
            embed.description = 'The upgrade failed.'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise

    @commands.command(name='upgrade-guilded', hidden=True, aliases=['upgrade-guilded-support'])
    async def upgrade_guilded(self, ctx, *, args=''):
        if not ctx.author.id in admins:
            return
        args = args.split(' ')
        force = False
        if 'force' in args:
            if not ctx.author.id == owner:
                return await ctx.send('Only the instance owner can force upgrades!')
            force = True
        embed = discord.Embed(title='Checking for upgrades...', description='Getting latest version from remote')
        msg = await ctx.send(embed=embed)
        try:
            os.system('rm -rf ' + os.getcwd() + '/update_check')
            status(os.system(
                'git clone --branch ' + branch + ' ' + files_endpoint + '/unifier-version.git ' + os.getcwd() + '/update_check'))
            with open('guilded.json', 'r') as file:
                current = json.load(file)
            with open('update_check/guilded.json', 'r') as file:
                new = json.load(file)
            release = new['release']
            version = new['version']
            update_available = new['release'] > current['release']
            if force:
                update_available = new['release'] >= current['release']
            try:
                desc = new['description']
            except:
                desc = 'No description is available for this upgrade.'
        except:
            embed.title = 'Failed to check for updates'
            embed.description = 'Could not find a valid upgrader.json file on remote'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        if not update_available:
            embed.title = 'No updates available'
            embed.description = 'Guilded Support is up-to-date.'
            embed.colour = 0x00ff00
            return await msg.edit(embed=embed)
        print('Upgrade available: ' + current['version'] + ' ==> ' + new['version'])
        print('Confirm upgrade through Discord.')
        embed.title = 'Update available'
        embed.description = f'An update is available for Guilded Support!\n\nCurrent version: {current["version"]} (`{current["release"]}`)\nNew version: {version} (`{release}`)\n\n{desc}'
        embed.colour = 0xffcc00
        row = [
            discord.ui.Button(style=discord.ButtonStyle.green, label='Upgrade', custom_id=f'accept', disabled=False),
            discord.ui.Button(style=discord.ButtonStyle.gray, label='Nevermind', custom_id=f'reject', disabled=False)
        ]
        btns = discord.ui.ActionRow(row[0], row[1])
        components = discord.ui.MessageComponents(btns)
        await msg.edit(embed=embed, components=components)

        def check(interaction):
            return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, preparing...')
        embed.title = 'Start the upgrade?'
        embed.description = '- :x: Your files have **not** been backed up, as this is not a Unifier upgrade.\n- :wrench: Any modifications you made to Guilded Support will be wiped, unless they are a part of the new upgrade.\n- :mobile_phone_off: Your Guilded bot instance will be powered off during the upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
        await interaction.response.edit_message(embed=embed, components=components)
        try:
            interaction = await self.bot.wait_for("component_interaction", check=check, timeout=60.0)
        except:
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await msg.edit(components=components)
        if interaction.custom_id == 'reject':
            row[0].disabled = True
            row[1].disabled = True
            btns = discord.ui.ActionRow(row[0], row[1])
            components = discord.ui.MessageComponents(btns)
            return await interaction.response.edit_message(components=components)
        print('Upgrade confirmed, upgrading Guilded Support...')
        print()
        embed.title = 'Upgrading Guilded Support'
        embed.description = ':hourglass_flowing_sand: Downloading updates\n:x: Installing updates\n:x: Reloading modules'
        await interaction.response.edit_message(embed=embed, components=None)
        log(type='UPG', status='info', content='Starting upgrade')
        try:
            log(type='GIT', status='info', content='Purging old update files')
            os.system('rm -rf ' + os.getcwd() + '/update_guilded')
            log(type='GIT', status='info', content='Downloading from remote repository...')
            status(os.system(
                'git clone --branch main ' + files_endpoint + '/unifier-guilded.git ' + os.getcwd() + '/update_guilded'))
            log(type='GIT', status='info', content='Confirming download...')
            x = open(os.getcwd() + '/update_guilded/bridge_guilded.py', 'r')
            x.close()
            log(type='GIT', status='ok', content='Download confirmed, proceeding with upgrade')
        except:
            log(type='UPG', status='error', content='Download failed, no rollback required')
            embed.title = 'Upgrade failed'
            embed.description = 'Could not download updates. No rollback is required.'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise
        try:
            log(type='INS', status='info', content='Installing upgrades')
            embed.description = ':white_check_mark: Downloading updates\n:hourglass_flowing_sand: Installing updates\n:x: Reloading modules'
            await msg.edit(embed=embed)
            log(type='INS', status='info', content='Stopping Guilded instance for upgrade')
            try:
                await self.bot.guilded_client.close()
                self.bot.guilded_client_task.cancel()
                del self.bot.guilded_client
                self.bot.unload_extension('cogs.bridge_guilded')
            except:
                pass
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update_guilded/bridge_guilded.py')
            status(os.system(
                'cp ' + os.getcwd() + '/update_guilded/bridge_guilded.py' + ' ' + os.getcwd() + '/cogs/bridge_guilded.py'))
            log(type='INS', status='info', content='Installing: ' + os.getcwd() + '/update_check/upgrader.json')
            status(
                os.system('cp ' + os.getcwd() + '/update_check/guilded.json' + ' ' + os.getcwd() + '/guilded.json'))
            embed.description = ':white_check_mark: Downloading updates\n:white_check_mark: Installing updates\n:hourglass_flowing_sand: Reloading modules'
            await msg.edit(embed=embed)
            log(type='UPG', status='ok', content='Restarting extension: cogs.bridge_guilded')
            try:
                self.bot.load_extension('cogs.bridge_guilded')
            except discord.ext.commands.errors.ExtensionNotLoaded:
                pass
            except:
                raise
            log(type='UPG', status='ok', content='Upgrade complete')
            embed.title = 'Upgrade successful'
            embed.description = 'The upgrade was successful! :partying_face:'
            embed.colour = 0x00ff00
            await msg.edit(embed=embed)
        except:
            log(type='UPG', status='error', content='Upgrade failed')
            embed.title = 'Upgrade failed'
            embed.description = 'The upgrade failed.'
            embed.colour = 0xff0000
            await msg.edit(embed=embed)
            raise

def setup(bot):
    bot.add_cog(Upgrader(bot))