// export async function sendChatRequest(newMessages: any[], currentChatId: number | undefined){
export async function sendChatRequest(message: any[], chatId?: number,){
  const url = chatId ? `/api/chat/${chatId}` : `/api/chat`
    try {
        const last = message[message.length-1]
        const payload = {
          role: "user",
          text: last?.content ?? "",
          prev_chats: message.slice(0, -1).map((m: any) => m.content), 
          chat_id: chatId,
          disease_code: last?.attachment?.disease_code ?? null,
          product_id: last?.attachment?.product_id ?? null,
        }

        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })

      if (!response.ok || !response.body) {
        const errorText = await response.text()
        throw new Error(`Server error: ${errorText || response.statusText}`)
      }

      const reader = response.body.getReader()                                                                                                                                           
      const decoder = new TextDecoder()
      let responseText = ''

      while (true) { 
        const { value, done } = await reader.read()
        if (done) break
        responseText += decoder.decode(value)
      } 
      return JSON.parse(responseText);
  } catch(error){
    console.error('An error occurred during the request:', error)
    return{
      error: "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
    };
  } 
}