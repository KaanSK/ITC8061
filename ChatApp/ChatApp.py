# Main program

from socket import *
import Utils as Util
import time
import getpass,re
import Configs as Config

print("Welcome to Ultra Needlessly Secure Chat APP.")
print("This is Demonstration Only version. You can Change The logger settings via Logs/Log-Config.json.")

SocketData = Util.PrepareSocket()

Util.Help()
if len(Config.NeighborTable) == 0:
    print("You dont have any Neighbour, to add use #ADDNEIGH")
while 1:
    if Config.Tokens[0]["WaitForListening"] != 1:
        user_input = Util.getLine();
        # Send Message
        if user_input is not None :
            if "#HELP" in user_input:
                Util.Help()
            elif "#ADDNEIGH" in user_input:
                remote_ip = input('Type Remote Ip Address >>')
                if Util.SearchDictionary(Config.NeighborTable,(remote_ip,SocketData['UDPaddr'][1]), 'Socket'):
                    print('This address already exists.')
                else:
                    header = Util.PrepareNeighborMessage(0x01)  # 0x01 => Initiation flag
                    UDPaddr = (remote_ip, SocketData['UDPaddr'][1])
                    Util.Send_Message(SocketData['UDPSocket'], UDPaddr, None, header)
            elif "#FILE" in user_input:
                 Util.Send_File(SocketData['UDPSocket'], SocketData['remote_addr'], user_input[5:].strip())
            elif "#ROUT" in user_input:
                Util.Send_RoutingTable(SocketData['UDPSocket'], SocketData['remote_addr'])
            elif user_input:
                if user_input.split(' ')[0].startswith('#'):
                    recipient_ID = user_input.split(' ')[0].split('#')[1]
                else:
                    print('Type #<Nick> to identify the receiver')
                    continue
                Recipient_Info, isNode = Util.Get_RecipientInfoFromNick(recipient_ID, SocketData['UDPSocket'])
                if isNode:
                    message_text = user_input[len(user_input.split(' ')[0]):].strip()
                    header = Util.PrepareRandomMessage(None, 0x04, Recipient_Info['UUID'])
                    Util.Send_Message(SocketData['UDPSocket'], Recipient_Info['Socket'], message_text, header)
                else:
                    print('AUTH Protocol taking place...')

                # else:
                # print "Session has not been established!"
    else:
        print(Config.Tokens[0]["WaitReason"] + " Please Wait.")
    # Receive Message
    received_data,remote_addr = Util.recv_flag(SocketData['UDPSocket'], SocketData['UDPBuff'])
    if not received_data:
        continue
    else:
        received_messages = Util.UnpackArray(received_data)

        #ADDNEIGH Message
        if received_messages[0].type == Util.MessageTypes.Auth.value and received_messages[0].flag == 0x01:
            Util.Send_ACKMessage(SocketData['UDPSocket'], remote_addr, Config.RoutingTable[0]['UUID'])
            header = Util.PrepareNeighborMessage(0x02)  # 0x02 => AuthSuccess flag
            Util.Send_Message(SocketData['UDPSocket'], remote_addr, None, header)
            print('Success Message Sent')

        #AUTH Message
        if received_messages[0].type == 1 and received_messages[0].flag == 16:
            Util.Set_Passphrase()
            all_msg = Util.ConcatMessages(received_messages)
            source_UUID = bytearray(received_messages[0].source).hex().upper()
            source_info = Util.SearchDictionary(Config.NeighborTable, source_UUID, 'UUID')
            Util.Get_AuthMessage(SocketData['UDPSocket'], SocketData['UDPaddr'], source_info['Socket'], all_msg,
                                 source_UUID)
        #ACK0 Message (NEIGH)
        if received_messages[0].type == Util.MessageTypes.Control.value and received_messages[0].flag == 0x04:
            if Util.SearchDictionary(Config.NeighborTable,bytearray(received_messages[0].source).hex().upper(), 'UUID') is None:
                remote_UUID = bytearray(received_messages[0].source).hex().upper()
                Util.Add_KeyIDTable(remote_UUID)
                neighbour_newline = {'UUID': remote_UUID, 'Socket': remote_addr,
                        'PassiveTimer': time.time()}
                Config.NeighborTable.append(dict(neighbour_newline))
                Util.Send_ACKMessage(SocketData['UDPSocket'], remote_addr, Config.RoutingTable[0]['UUID'])
                print('Added to Neigh. Table.')
                Util.Print_Table(Config.KeyIDs)
            Util.Tokens[0]["WaitForListening"] = 0;
            Util.Tokens[0]["WaitReason"] = None;
            print('ACK0 Received')

            #ACK1 Message (NEIGH)
            if len(received_messages) > 1 and received_messages[1].type == Util.MessageTypes.Auth.value and received_messages[1].flag == 0x02:
                remote_UUID = bytearray(received_messages[0].source).hex().upper()
                Util.Add_KeyIDTable(remote_UUID)
                newline = {'UUID':bytearray(received_messages[0].source).hex().upper(), 'Socket': remote_addr, 'PassiveTimer': time.time()}
                Config.NeighborTable.append(dict(newline))
                print('Added to Neigh. Table.')
                Util.Send_ACKMessage(SocketData['UDPSocket'], remote_addr, Config.RoutingTable[0]['UUID'])
                print('Session Established') #WAITING ACK!!!!
                continue
        if received_messages[0].type == 16:
            Util.WritePacketsToFile(received_messages)
            continue
        elif received_messages[0].type == 64:
            Util.Get_RoutingTable(Util.ConcatMessages(received_messages), received_messages[0].source)
            print("Received message '", Util.ConcatMessages(received_messages), "'")
            continue
            # End Receiving Message
        elif received_messages[0].type == Util.MessageTypes.Data.value and received_messages[0].flag != 16:
            encrypted_text = Util.ConcatMessages(received_messages)
            print("Received message '", encrypted_text, "'")
            continue

SocketData['UDPSocket'].close()